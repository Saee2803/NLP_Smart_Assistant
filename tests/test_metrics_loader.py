from metrics_engine.metrics_loader import OEMMetricsLoader

def test_oem_metrics_loader():
    loader = OEMMetricsLoader("data/oem_metrics_25.csv")
    events = loader.load_metrics()

    assert len(events) > 0
    assert "timestamp" in events[0]
    assert "metric_name" in events[0]

