# --- OCI API authentication (OCI console -> Profile -> API keys -> Add API key) ---
variable "tenancy_ocid" { type = string }
variable "user_ocid" { type = string }
variable "fingerprint" { type = string }
variable "private_key_path" { type = string }
variable "region" {
  type        = string
  description = "Your HOME region, e.g. ca-toronto-1. Always Free resources only exist there."
}

variable "compartment_ocid" {
  type        = string
  default     = null
  description = "Defaults to the tenancy (root compartment)."
}

# --- VM sizing: stays inside the Always Free A1 allowance (2 OCPU / 12 GB as of mid-2026) ---
variable "ocpus" {
  type    = number
  default = 2
  validation {
    condition     = var.ocpus <= 2
    error_message = "Always Free A1 allowance is 2 OCPUs. Going above this costs money."
  }
}

variable "memory_gb" {
  type    = number
  default = 12
  validation {
    condition     = var.memory_gb <= 12
    error_message = "Always Free A1 allowance is 12 GB. Going above this costs money."
  }
}

variable "boot_volume_gb" {
  type    = number
  default = 100
  validation {
    condition     = var.boot_volume_gb >= 50 && var.boot_volume_gb <= 200
    error_message = "Always Free block storage is 200 GB total."
  }
}

# --- Access ---
variable "ssh_public_key_path" {
  type    = string
  default = "~/.ssh/id_ed25519.pub"
}

variable "admin_cidr" {
  type        = string
  description = "Your public IP as x.x.x.x/32. SSH is only open to this address (break-glass access)."
}

variable "tailscale_auth_key" {
  type        = string
  sensitive   = true
  description = "Tailscale reusable auth key. All service ports are reached through Tailscale, never the internet."
}

variable "alert_email" {
  type        = string
  description = "Gets an email if the account spends a single cent."
}

variable "project" {
  type    = string
  default = "aml"
}
