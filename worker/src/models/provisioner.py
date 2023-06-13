from dataclasses import dataclass

from dataclasses_json import dataclass_json


@dataclass_json
@dataclass(order=True, frozen=True)
class ProvisionerValue(object):
    cursor: str
    last_scrapet: int | None = None

    def copy_with(self, cursor: str | None = None, last_scrapet: int | None = None):
        return ProvisionerValue(
            cursor=cursor or self.cursor,
            last_scrapet=last_scrapet or self.last_scrapet,
        )


@dataclass(order=True, frozen=True)
class ProvisionerKey(object):
    on: bool
    domain: str
    provisioner_id: str | None = None
    time_id: int | None = None

    def __str__(self) -> str:
        if self.provisioner_id:
            assert self.time_id
            assert self.on
            return f"provisioner:on:{self.time_id}:{self.provisioner_id}:{self.domain}"

        assert not self.on
        return f"provisioner:off:{self.domain}"

    def turn_off(self):
        assert self.on
        return ProvisionerKey(
            on=False,
            domain=self.domain,
        )

    @classmethod
    def from_string(cls, string: str):
        parts = string.split(":")
        if len(parts) == 5:
            _, on, time_id, provisioner_id, domain = parts
            assert on == "on"

            return ProvisionerKey(
                domain=domain,
                on=True,
                provisioner_id=provisioner_id,
                time_id=time_id,
            )

        elif len(parts) == 3:
            _, off, domain = parts
            assert off == "off"

            return ProvisionerKey(
                domain=domain,
                on=False,
                provisioner_id=None,
                time_id=None,
            )

        raise ValueError(f'invalid string "{string}"')
