from app.tasks import notifications as notifications_task


def test_process_detection_event_task_is_registered_under_expected_name():
    assert "app.tasks.notifications.process_detection_event" in notifications_task.celery_app.tasks


def test_process_detection_event_invokes_async_processor(monkeypatch):
    called_with = {}

    async def fake_processor(event_id: int) -> None:
        called_with["event_id"] = event_id

    monkeypatch.setattr(notifications_task, "_process_detection_event_async", fake_processor)

    notifications_task.process_detection_event.run(42)

    assert called_with["event_id"] == 42
