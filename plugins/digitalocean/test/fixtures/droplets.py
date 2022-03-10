droplets = [
    {
        "id": 289110074,
        "name": "ubuntu-s-1vcpu-1gb-fra1-01",
        "memory": 1024,
        "vcpus": 1,
        "disk": 25,
        "locked": False,
        "status": "active",
        "kernel": None,
        "created_at": "2022-03-03T16:26:55Z",
        "features": [
            "droplet_agent",
            "private_networking"
        ],
        "backup_ids": [],
        "next_backup_window": None,
        "snapshot_ids": [
            103198134
        ],
        "image": {
            "id": 101111514,
            "name": "20.04 (LTS) x64",
            "distribution": "Ubuntu",
            "slug": "ubuntu-20-04-x64",
            "public": True,
            "regions": [
                "nyc3",
                "nyc1",
                "sfo1",
                "nyc2",
                "ams2",
                "sgp1",
                "lon1",
                "ams3",
                "fra1",
                "tor1",
                "sfo2",
                "blr1",
                "sfo3"
            ],
            "created_at": "2022-02-01T16:53:57Z",
            "min_disk_size": 15,
            "type": "base",
            "size_gigabytes": 0.61,
            "description": "Ubuntu 20.04 x86",
            "tags": [],
            "status": "available"
        },
        "volume_ids": [
            "631f81d2-9fc1-11ec-800c-0a58ac14d197"
        ],
        "size": {
            "slug": "s-1vcpu-1gb",
            "memory": 1024,
            "vcpus": 1,
            "disk": 25,
            "transfer": 1.0,
            "price_monthly": 5.0,
            "price_hourly": 0.00744,
            "regions": [
                "ams3",
                "blr1",
                "fra1",
                "lon1",
                "nyc1",
                "nyc3",
                "sfo3",
                "sgp1",
                "tor1"
            ],
            "available": True,
            "description": "Basic"
        },
        "size_slug": "s-1vcpu-1gb",
        "networks": {
            "v4": [
                {
                    "ip_address": "127.0.0.1",
                    "netmask": "255.255.240.0",
                    "gateway": "127.0.0.1",
                    "type": "private"
                },
                {
                    "ip_address": "127.0.0.1",
                    "netmask": "255.255.240.0",
                    "gateway": "127.0.0.1",
                    "type": "public"
                },
                {
                    "ip_address": "127.0.0.1",
                    "netmask": "255.255.252.0",
                    "gateway": "127.0.0.1",
                    "type": "public"
                }
            ],
            "v6": []
        },
        "region": {
            "name": "Frankfurt 1",
            "slug": "fra1",
            "features": [
                "backups",
                "ipv6",
                "metadata",
                "install_agent",
                "storage",
                "image_transfer"
            ],
            "available": True,
            "sizes": [
                "s-1vcpu-1gb",
                "s-1vcpu-1gb-amd",
                "s-1vcpu-1gb-intel",
                "s-1vcpu-2gb",
                "s-1vcpu-2gb-amd",
                "s-1vcpu-2gb-intel",
                "s-2vcpu-2gb",
                "s-2vcpu-2gb-amd",
                "s-2vcpu-2gb-intel",
                "s-2vcpu-4gb",
                "s-2vcpu-4gb-amd",
                "s-2vcpu-4gb-intel",
                "s-4vcpu-8gb",
                "c-2",
                "c2-2vcpu-4gb",
                "s-4vcpu-8gb-amd",
                "s-4vcpu-8gb-intel",
                "g-2vcpu-8gb",
                "gd-2vcpu-8gb",
                "s-8vcpu-16gb",
                "m-2vcpu-16gb",
                "c-4",
                "c2-4vcpu-8gb",
                "s-8vcpu-16gb-amd",
                "s-8vcpu-16gb-intel",
                "m3-2vcpu-16gb",
                "g-4vcpu-16gb",
                "so-2vcpu-16gb",
                "m6-2vcpu-16gb",
                "gd-4vcpu-16gb",
                "so1_5-2vcpu-16gb",
                "m-4vcpu-32gb",
                "c-8",
                "c2-8vcpu-16gb",
                "m3-4vcpu-32gb",
                "g-8vcpu-32gb",
                "so-4vcpu-32gb",
                "m6-4vcpu-32gb",
                "gd-8vcpu-32gb",
                "so1_5-4vcpu-32gb",
                "m-8vcpu-64gb",
                "c-16",
                "c2-16vcpu-32gb",
                "m3-8vcpu-64gb",
                "g-16vcpu-64gb",
                "so-8vcpu-64gb",
                "m6-8vcpu-64gb",
                "gd-16vcpu-64gb",
                "so1_5-8vcpu-64gb",
                "m-16vcpu-128gb",
                "c-32",
                "c2-32vcpu-64gb",
                "m3-16vcpu-128gb",
                "m-24vcpu-192gb",
                "g-32vcpu-128gb",
                "so-16vcpu-128gb",
                "m6-16vcpu-128gb",
                "gd-32vcpu-128gb",
                "m3-24vcpu-192gb",
                "g-40vcpu-160gb",
                "so1_5-16vcpu-128gb",
                "m-32vcpu-256gb",
                "gd-40vcpu-160gb",
                "so-24vcpu-192gb",
                "m6-24vcpu-192gb",
                "m3-32vcpu-256gb",
                "so1_5-24vcpu-192gb",
                "so-32vcpu-256gb",
                "m6-32vcpu-256gb",
                "so1_5-32vcpu-256gb"
            ]
        },
        "tags": [],
        "vpc_uuid": "0d3176ad-41e0-4021-b831-0c5c45c60959"
    },
    {
        "id": 290075243,
        "name": "pool-1g2g56zow-u9fs4",
        "memory": 2048,
        "vcpus": 1,
        "disk": 50,
        "locked": False,
        "status": "active",
        "kernel": None,
        "created_at": "2022-03-10T13:10:50Z",
        "features": [
            "private_networking"
        ],
        "backup_ids": [],
        "next_backup_window": None,
        "snapshot_ids": [],
        "image": {
            "id": 103151528,
            "name": "do-kube-1.22.7-do.0",
            "distribution": "Debian",
            "slug": None,
            "public": False,
            "regions": [
                "nyc1",
                "sfo1",
                "nyc2",
                "ams2",
                "sgp1",
                "lon1",
                "nyc3",
                "ams3",
                "fra1",
                "tor1",
                "sfo2",
                "blr1",
                "sfo3"
            ],
            "created_at": "2022-03-02T23:31:14Z",
            "min_disk_size": 25,
            "type": "admin",
            "size_gigabytes": 6.55,
            "tags": [],
            "status": "available"
        },
        "volume_ids": [],
        "size": {
            "slug": "s-1vcpu-2gb",
            "memory": 2048,
            "vcpus": 1,
            "disk": 50,
            "transfer": 2.0,
            "price_monthly": 10.0,
            "price_hourly": 0.01488,
            "regions": [
                "ams3",
                "blr1",
                "fra1",
                "lon1",
                "nyc1",
                "nyc3",
                "sfo3",
                "sgp1",
                "tor1"
            ],
            "available": True,
            "description": "Basic"
        },
        "size_slug": "s-1vcpu-2gb",
        "networks": {
            "v4": [
                {
                    "ip_address": "127.0.0.1",
                    "netmask": "255.255.240.0",
                    "gateway": "127.0.0.1",
                    "type": "private"
                },
                {
                    "ip_address": "127.0.0.1",
                    "netmask": "255.255.240.0",
                    "gateway": "127.0.0.1",
                    "type": "public"
                }
            ],
            "v6": []
        },
        "region": {
            "name": "Frankfurt 1",
            "slug": "fra1",
            "features": [
                "backups",
                "ipv6",
                "metadata",
                "install_agent",
                "storage",
                "image_transfer"
            ],
            "available": True,
            "sizes": [
                "s-1vcpu-1gb",
                "s-1vcpu-1gb-amd",
                "s-1vcpu-1gb-intel",
                "s-1vcpu-2gb",
                "s-1vcpu-2gb-amd",
                "s-1vcpu-2gb-intel",
                "s-2vcpu-2gb",
                "s-2vcpu-2gb-amd",
                "s-2vcpu-2gb-intel",
                "s-2vcpu-4gb",
                "s-2vcpu-4gb-amd",
                "s-2vcpu-4gb-intel",
                "s-4vcpu-8gb",
                "c-2",
                "c2-2vcpu-4gb",
                "s-4vcpu-8gb-amd",
                "s-4vcpu-8gb-intel",
                "g-2vcpu-8gb",
                "gd-2vcpu-8gb",
                "s-8vcpu-16gb",
                "m-2vcpu-16gb",
                "c-4",
                "c2-4vcpu-8gb",
                "s-8vcpu-16gb-amd",
                "s-8vcpu-16gb-intel",
                "m3-2vcpu-16gb",
                "g-4vcpu-16gb",
                "so-2vcpu-16gb",
                "m6-2vcpu-16gb",
                "gd-4vcpu-16gb",
                "so1_5-2vcpu-16gb",
                "m-4vcpu-32gb",
                "c-8",
                "c2-8vcpu-16gb",
                "m3-4vcpu-32gb",
                "g-8vcpu-32gb",
                "so-4vcpu-32gb",
                "m6-4vcpu-32gb",
                "gd-8vcpu-32gb",
                "so1_5-4vcpu-32gb",
                "m-8vcpu-64gb",
                "c-16",
                "c2-16vcpu-32gb",
                "m3-8vcpu-64gb",
                "g-16vcpu-64gb",
                "so-8vcpu-64gb",
                "m6-8vcpu-64gb",
                "gd-16vcpu-64gb",
                "so1_5-8vcpu-64gb",
                "m-16vcpu-128gb",
                "c-32",
                "c2-32vcpu-64gb",
                "m3-16vcpu-128gb",
                "m-24vcpu-192gb",
                "g-32vcpu-128gb",
                "so-16vcpu-128gb",
                "m6-16vcpu-128gb",
                "gd-32vcpu-128gb",
                "m3-24vcpu-192gb",
                "g-40vcpu-160gb",
                "so1_5-16vcpu-128gb",
                "m-32vcpu-256gb",
                "gd-40vcpu-160gb",
                "so-24vcpu-192gb",
                "m6-24vcpu-192gb",
                "m3-32vcpu-256gb",
                "so1_5-24vcpu-192gb",
                "so-32vcpu-256gb",
                "m6-32vcpu-256gb",
                "so1_5-32vcpu-256gb"
            ]
        },
        "tags": [
            "k8s",
            "k8s:worker",
            "k8s:e1c48631-b382-4001-2168-c47c54795a26"
        ],
        "vpc_uuid": "0d3176ad-41e0-4021-b831-0c5c45c60959"
    }
]
