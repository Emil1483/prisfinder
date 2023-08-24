from dataclasses import dataclass
from enum import Enum
from types import NoneType

from dataclasses_json import dataclass_json


class ProvisionerStatus(Enum):
    ON = "on"
    OFF = "off"
    DISABLED = "disabled"

    def __deepcopy__(self, memo):
        return self.value

    def __str__(self) -> str:
        return self.value

    def __eq__(self, __value: object) -> bool:
        return __value == self.value


@dataclass_json
@dataclass(order=True)
class ProvisionerValue(object):
    cursor: str
    last_scraped: int | None = None

    def __post_init__(self):
        assert isinstance(self.cursor, str)
        assert isinstance(self.last_scraped, (NoneType, int))


@dataclass(order=True, frozen=True)
class ProvisionerKey(object):
    status: ProvisionerStatus
    domain: str
    provisioner_id: str | None = None
    time_id: int | None = None

    def __post_init__(self):
        assert isinstance(self.status, ProvisionerStatus)
        assert isinstance(self.domain, str)
        assert isinstance(self.provisioner_id, (str, NoneType))
        assert isinstance(self.time_id, (int, NoneType))

    def __str__(self) -> str:
        if self.provisioner_id:
            assert self.time_id is not None
            assert self.status is ProvisionerStatus.ON
            return f"provisioner:{self.status}:{self.time_id}:{self.provisioner_id}:{self.domain}"

        return f"provisioner:{self.status}:{self.domain}"

    def set_status(self, status: ProvisionerStatus):
        assert self.status == ProvisionerStatus.ON
        return ProvisionerKey(
            status=status,
            domain=self.domain,
        )

    @classmethod
    def from_string(cls, string: str):
        parts = string.split(":")
        if len(parts) == 5:
            _, status, time_id, provisioner_id, domain = parts
            assert status == ProvisionerStatus.ON

            return ProvisionerKey(
                domain=domain,
                status=ProvisionerStatus.ON,
                provisioner_id=provisioner_id,
                time_id=int(time_id),
            )

        elif len(parts) == 3:
            _, status, domain = parts
            assert status in (
                ProvisionerStatus.OFF.value,
                ProvisionerStatus.DISABLED.value,
            )

            return ProvisionerKey(
                domain=domain,
                status=ProvisionerStatus.OFF,
                provisioner_id=None,
                time_id=None,
            )

        raise ValueError(f'invalid string "{string}"')
