import pytest

from app.domain.entities import WatchTarget
from app.monitor.scheduler import Scheduler


class FakeWatchTargetRepo:
    def __init__(self, due: list[WatchTarget]) -> None:
        self._due = due

    async def list_due(self, now):
        return self._due


class FakeMonitoringService:
    def __init__(self, fail_for: set[int] | None = None) -> None:
        self.checked: list[int] = []
        self._fail_for = fail_for or set()

    async def check_watch_target(self, watch_target: WatchTarget):
        if watch_target.id in self._fail_for:
            raise RuntimeError("provider crashed")
        self.checked.append(watch_target.id)
        return []


@pytest.mark.asyncio
async def test_tick_checks_every_due_target():
    targets = [
        WatchTarget(
            id=1,
            retailer_slug="blinkit",
            city="Bengaluru",
            pincode="560001",
            keyword="milk",
        ),
        WatchTarget(
            id=2,
            retailer_slug="zepto",
            city="Bengaluru",
            pincode="560001",
            keyword="bread",
        ),
    ]
    repo = FakeWatchTargetRepo(due=targets)
    service = FakeMonitoringService()
    scheduler = Scheduler(watch_target_repo=repo, monitoring_service=service)

    await scheduler.tick()

    assert sorted(service.checked) == [1, 2]


@pytest.mark.asyncio
async def test_tick_continues_past_a_failing_target():
    targets = [
        WatchTarget(
            id=1,
            retailer_slug="blinkit",
            city="Bengaluru",
            pincode="560001",
            keyword="milk",
        ),
        WatchTarget(
            id=2,
            retailer_slug="blinkit",
            city="Bengaluru",
            pincode="560001",
            keyword="bread",
        ),
    ]
    repo = FakeWatchTargetRepo(due=targets)
    service = FakeMonitoringService(fail_for={1})
    scheduler = Scheduler(watch_target_repo=repo, monitoring_service=service)

    await scheduler.tick()

    assert service.checked == [2]
