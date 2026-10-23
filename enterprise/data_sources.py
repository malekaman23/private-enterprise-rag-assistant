"""Data-source catalog and safe capability metadata.

The catalog is provider-neutral: a company can keep data in a local share,
object storage, SaaS drive, database, ERP, or a private API. Actual credentials
and provider SDKs belong in a connector gateway and are never returned here.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DataSourceSpec:
    key: str
    name: str
    category: str
    access_mode: str
    description: str
    requires_gateway: bool = False


DATA_SOURCES = (
    DataSourceSpec("local_folder", "Local folder", "filesystem", "read_only", "A folder on the private host"),
    DataSourceSpec("smb_nas", "SMB / Windows file server / NAS", "filesystem", "read_only", "Company shares and Windows file servers"),
    DataSourceSpec("nfs_nas", "NFS / Linux file server / NAS", "filesystem", "read_only", "Mounted Linux or Unix shares"),
    DataSourceSpec("s3", "Amazon S3 / S3-compatible storage", "object_storage", "read_only", "S3, MinIO, Ceph and compatible stores", True),
    DataSourceSpec("azure_blob", "Azure Blob Storage", "object_storage", "read_only", "Private Azure storage containers", True),
    DataSourceSpec("gcs", "Google Cloud Storage", "object_storage", "read_only", "Private GCS buckets", True),
    DataSourceSpec("sharepoint", "SharePoint / OneDrive", "saas_drive", "read_only", "Microsoft 365 document libraries", True),
    DataSourceSpec("google_drive", "Google Drive", "saas_drive", "read_only", "Google Workspace files", True),
    DataSourceSpec("dropbox", "Dropbox / Box", "saas_drive", "read_only", "Approved cloud file providers", True),
    DataSourceSpec("postgresql", "PostgreSQL / MySQL / SQL database", "database", "read_only", "Approved read-only views and analytics", True),
    DataSourceSpec("erp_crm", "ERP / CRM", "business_system", "read_only", "Sales, finance and operations systems", True),
    DataSourceSpec("private_api", "Private company API", "api", "read_only", "Internal REST or GraphQL data service", True),
)


def catalog() -> list[dict]:
    return [
        {
            "key": item.key,
            "name": item.name,
            "category": item.category,
            "access_mode": item.access_mode,
            "description": item.description,
            "requires_gateway": item.requires_gateway,
            "status": "setup_required",
        }
        for item in DATA_SOURCES
    ]

