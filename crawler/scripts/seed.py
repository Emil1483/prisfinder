from src.services.prisma_service import clear_tables
from src.services.redis_service import RedisService


def seed():
    with RedisService.from_env_url() as r:
        r.insert_provisioner("", priority=0, domain="finn.no")
        r.insert_provisioner(
            "https://www.power.no/tv-og-lyd/hodetelefoner/true-wireless-hodetelefoner/samsung-galaxy-buds2-pro-true-wireless-bora-purple/p-1646111/"
        )


if __name__ == "__main__":
    seed()
