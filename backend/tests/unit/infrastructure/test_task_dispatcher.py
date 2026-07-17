from app.infrastructure.tasks_dispatch import CeleryTaskDispatcher


class FakeCeleryApp:
    def __init__(self) -> None:
        self.sent: list[tuple[str, list]] = []

    def send_task(self, name: str, args: list):
        self.sent.append((name, args))


def test_dispatch_detection_event_sends_task_by_name():
    fake_app = FakeCeleryApp()
    dispatcher = CeleryTaskDispatcher(fake_app)

    dispatcher.dispatch_detection_event(42)

    assert fake_app.sent == [("app.tasks.notifications.process_detection_event", [42])]
