locals {
  compartment = coalesce(var.compartment_ocid, var.tenancy_ocid)
  tags        = { project = var.project, managed_by = "terraform" }
}

data "oci_identity_availability_domains" "ads" {
  compartment_id = var.tenancy_ocid
}

# Latest Ubuntu 24.04 image built for ARM (A1) shapes.
data "oci_core_images" "ubuntu_arm" {
  compartment_id           = local.compartment
  operating_system         = "Canonical Ubuntu"
  operating_system_version = "24.04"
  shape                    = "VM.Standard.A1.Flex"
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
}

data "oci_objectstorage_namespace" "ns" {
  compartment_id = local.compartment
}

# ---------------- Network ----------------
resource "oci_core_vcn" "main" {
  compartment_id = local.compartment
  cidr_blocks    = ["10.0.0.0/16"]
  display_name   = "${var.project}-vcn"
  dns_label      = var.project
  freeform_tags  = local.tags
}

resource "oci_core_internet_gateway" "igw" {
  compartment_id = local.compartment
  vcn_id         = oci_core_vcn.main.id
  display_name   = "${var.project}-igw"
  freeform_tags  = local.tags
}

resource "oci_core_route_table" "public" {
  compartment_id = local.compartment
  vcn_id         = oci_core_vcn.main.id
  display_name   = "${var.project}-public-rt"
  route_rules {
    destination       = "0.0.0.0/0"
    network_entity_id = oci_core_internet_gateway.igw.id
  }
  freeform_tags = local.tags
}

# Default deny. Only SSH from your IP (break-glass) and Tailscale's UDP port are open.
# Kafka, Temporal, MLflow etc. are NOT exposed to the internet; you reach them over Tailscale.
resource "oci_core_security_list" "vm" {
  compartment_id = local.compartment
  vcn_id         = oci_core_vcn.main.id
  display_name   = "${var.project}-vm-sl"

  egress_security_rules {
    destination = "0.0.0.0/0"
    protocol    = "all"
  }

  ingress_security_rules {
    source   = var.admin_cidr
    protocol = "6" # TCP
    tcp_options {
      min = 22
      max = 22
    }
  }

  ingress_security_rules {
    source   = "0.0.0.0/0"
    protocol = "17" # UDP, lets Tailscale make direct (faster) connections
    udp_options {
      min = 41641
      max = 41641
    }
  }
  freeform_tags = local.tags
}

resource "oci_core_subnet" "public" {
  compartment_id    = local.compartment
  vcn_id            = oci_core_vcn.main.id
  cidr_block        = "10.0.1.0/24"
  display_name      = "${var.project}-public"
  dns_label         = "pub"
  route_table_id    = oci_core_route_table.public.id
  security_list_ids = [oci_core_security_list.vm.id]
  freeform_tags     = local.tags
}

# ---------------- Compute ----------------
resource "oci_core_instance" "vm" {
  compartment_id      = local.compartment
  availability_domain = data.oci_identity_availability_domains.ads.availability_domains[0].name
  display_name        = "${var.project}-vm"
  shape               = "VM.Standard.A1.Flex"

  shape_config {
    ocpus         = var.ocpus
    memory_in_gbs = var.memory_gb
  }

  source_details {
    source_type             = "image"
    source_id               = data.oci_core_images.ubuntu_arm.images[0].id
    boot_volume_size_in_gbs = var.boot_volume_gb
  }

  create_vnic_details {
    subnet_id        = oci_core_subnet.public.id
    assign_public_ip = true
    hostname_label   = "${var.project}-vm"
  }

  metadata = {
    ssh_authorized_keys = file(pathexpand(var.ssh_public_key_path))
    user_data = base64encode(templatefile("${path.module}/cloud-init.yaml.tftpl", {
      tailscale_auth_key = var.tailscale_auth_key
      hostname           = "${var.project}-vm"
    }))
  }

  # A new image version must not silently replace the VM (and wipe its data).
  lifecycle {
    ignore_changes = [source_details[0].source_id, metadata["user_data"]]
  }
  freeform_tags = local.tags
}

# ---------------- Object storage (MLflow artifacts, model files) ----------------
resource "oci_objectstorage_bucket" "mlflow" {
  compartment_id = local.compartment
  namespace      = data.oci_objectstorage_namespace.ns.namespace
  name           = "${var.project}-mlflow-artifacts"
  access_type    = "NoPublicAccess"
  versioning     = "Enabled"
  freeform_tags  = local.tags
}

# ---------------- Cost guardrail ----------------
# Real teams put budgets on every account. This emails you if spend reaches $0.01.
resource "oci_budget_budget" "guardrail" {
  compartment_id = var.tenancy_ocid
  amount         = 1
  reset_period   = "MONTHLY"
  target_type    = "COMPARTMENT"
  targets        = [local.compartment]
  display_name   = "${var.project}-zero-spend-guardrail"
}

resource "oci_budget_alert_rule" "any_spend" {
  budget_id      = oci_budget_budget.guardrail.id
  type           = "ACTUAL"
  threshold      = 1
  threshold_type = "PERCENTAGE"
  recipients     = var.alert_email
  display_name   = "any-spend"
  message        = "OCI spend detected on the AML project. Check for resources outside Always Free."
}
