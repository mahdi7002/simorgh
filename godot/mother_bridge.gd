extends Node

signal mother_state_received(state: Dictionary)
signal mother_state_failed(message: String)

@export var mother_url := "http://127.0.0.1:8010/api/mother/state"
@export var poll_seconds := 10.0

var _http: HTTPRequest
var _timer: Timer

func _ready() -> void:
    _http = HTTPRequest.new()
    add_child(_http)
    _http.request_completed.connect(_on_request_completed)

    _timer = Timer.new()
    _timer.wait_time = max(1.0, poll_seconds)
    _timer.autostart = true
    _timer.timeout.connect(poll)
    add_child(_timer)

    poll()

func poll() -> void:
    if _http.get_http_client_status() != HTTPClient.STATUS_DISCONNECTED:
        return
    var err := _http.request(mother_url)
    if err != OK:
        mother_state_failed.emit("Mother request failed: %s" % err)

func _on_request_completed(
    result: int,
    response_code: int,
    _headers: PackedStringArray,
    body: PackedByteArray
) -> void:
    if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
        mother_state_failed.emit("Mother HTTP status: %s" % response_code)
        return

    var parsed = JSON.parse_string(body.get_string_from_utf8())
    if typeof(parsed) != TYPE_DICTIONARY:
        mother_state_failed.emit("Mother returned invalid JSON")
        return

    mother_state_received.emit(parsed)

func latest_snapshot(state: Dictionary) -> Dictionary:
    return state.get("snapshot", {})

func daily_report(state: Dictionary) -> Dictionary:
    return state.get("daily", {})

func weekly_report(state: Dictionary) -> Dictionary:
    return state.get("weekly", {})

func boot_report(state: Dictionary) -> Dictionary:
    return state.get("post_boot", {})

func goals(state: Dictionary) -> Array:
    return state.get("goals", [])
