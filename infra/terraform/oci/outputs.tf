output "vm_public_ip" {
  value       = oci_core_instance.vm.public_ip
  description = "Break-glass SSH only. Day to day, use the Tailscale name aml-vm."
}

output "tailscale_hostname" {
  value = "${var.project}-vm"
}

output "mlflow_bucket" {
  value = oci_objectstorage_bucket.mlflow.name
}

output "s3_compat_endpoint" {
  value       = "https://${data.oci_objectstorage_namespace.ns.namespace}.compat.objectstorage.${var.region}.oraclecloud.com"
  description = "Put this in MLFLOW_S3_ENDPOINT_URL in .env.cloud"
}
