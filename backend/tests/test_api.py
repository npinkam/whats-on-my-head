def test_health_endpoint(test_client):
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_ready_endpoint(test_client):
    response = test_client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_websocket_connection(test_client):
    with test_client.websocket_connect("/ws/test-client") as websocket:
        assert websocket is not None


def test_websocket_send_location(test_client):
    with test_client.websocket_connect("/ws/test-client") as websocket:
        websocket.send_json({"latitude": 40.7128, "longitude": -74.0060})


def test_websocket_disconnect(test_client):
    with test_client.websocket_connect("/ws/test-client") as websocket:
        websocket.send_json({"latitude": 40.7128, "longitude": -74.0060})
    manager = test_client.app.state.manager
    assert len(manager.active_connections) == 0
