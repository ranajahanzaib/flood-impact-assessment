import pytest

from ml.datasets.impactmesh import ImpactMeshDownloader


def test_dataset_listing():
    downloader = ImpactMeshDownloader()
    events = downloader.list_events()
    assert len(events) >= 4
    event_ids = [e["event_id"] for e in events]
    assert "EMSR548_GER" in event_ids
    assert "EMSR590_PAK" in event_ids

def test_dataset_split_filtering():
    downloader = ImpactMeshDownloader()
    test_events = downloader.list_events(split="test")
    assert all(e["split"] == "test" for e in test_events)
    assert any(e["event_id"] == "EMSR548_GER" for e in test_events)

    held_out_events = downloader.list_events(split="held_out")
    assert all(e["split"] == "held_out" for e in held_out_events)
    assert any(e["event_id"] == "EMSR601_ESP" for e in held_out_events)

def test_selective_download_budget_enforcement():
    downloader = ImpactMeshDownloader()
    # Test valid download plan within budget
    res = downloader.download_events(
        event_ids=["EMSR548_GER"],
        max_download_gb=5.0
    )
    assert res["status"] == "ready"
    assert "EMSR548_GER" in res["events_selected"]

    # Test exceeding budget throws ValueError
    with pytest.raises(ValueError, match="Download would exceed limit"):
        downloader.download_events(
            event_ids=["EMSR548_GER", "EMSR590_PAK"],
            max_download_gb=0.5  # 500 MB limit, while GER+PAK is > 1000 MB
        )

def test_invalid_event_handling():
    downloader = ImpactMeshDownloader()
    with pytest.raises(ValueError, match="not found in ImpactMesh catalog"):
        downloader.download_events(event_ids=["NON_EXISTENT_EVENT_ID"])
