from dataclasses import dataclass
from enum import Enum
from types import NoneType

from dataclasses_json import dataclass_json

from src.models.url import URLStatus


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
@dataclass(order=True, frozen=True)
class ProvisionerValue(object):
    cursor_waiting: str | None = None
    cursor_completed: str | None = None
    cursor_failed: str | None = None
    last_scrapet: int | None = None

    def with_cursor_none(self, status: URLStatus):
        completed = status == URLStatus.COMPLETED
        return ProvisionerValue(
            cursor_waiting=self.cursor_waiting if status != URLStatus.WAITING else None,
            cursor_failed=self.cursor_failed if status != URLStatus.FAILED else None,
            cursor_completed=self.cursor_completed if not completed else None,
            last_scrapet=self.last_scrapet,
        )

    def copy_with(
        self,
        cursor: str | None = None,
        url_status: str | None = None,
        last_scrapet: int | None = None,
    ):
        assert (cursor is None) == (url_status is None)

        return ProvisionerValue(
            cursor_waiting=cursor
            if url_status == URLStatus.WAITING
            else self.cursor_waiting,
            cursor_failed=cursor
            if url_status == URLStatus.FAILED
            else self.cursor_failed,
            cursor_completed=cursor
            if url_status == URLStatus.COMPLETED
            else self.cursor_completed,
            last_scrapet=last_scrapet or self.last_scrapet,
        )

    def __post_init__(self):
        assert isinstance(self.cursor_waiting, (NoneType, str))
        assert isinstance(self.cursor_completed, (NoneType, str))
        assert isinstance(self.cursor_failed, (NoneType, str))
        assert isinstance(self.last_scrapet, (NoneType, int))


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
