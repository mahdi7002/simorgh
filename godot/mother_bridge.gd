extends Node

signal mother_state_received(state: Dictionary)
signal mother_state_failed(message: String)
signal mother_changes_received(changes: Array)

@export var mother_url := "http://127.0.0.1:8010/api/mother/state"
@export var poll_seconds := 10.0
@export var changes_url := "http://127.0.0.1:8010/api/mother/changes"

var _http: HTTPRequest
var _last_change_timestamp := ""
var _timer: Timer

func _ready() -> void:
    _http = HTTPRequest.new()
    add_child(_http)
    _http.request_completed.connect(_on_request_completed)

    _timer = Timer.new()
    _timer.wait_time = max(1.0, poll_seconds)
    _timer.autostart = true
    _timer.timeout.connect(_poll_all)
    add_child(_timer)

    _poll_all()

func _poll_all() -> void:
    poll()
    poll_changes()

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


func poll_changes() -> void:
    var url := changes_url
    if _last_change_timestamp != "":
        url += "?since=" + _last_change_timestamp.uri_encode()
    var request := HTTPRequest.new()
    add_child(request)
    request.request_completed.connect(func(result, response_code, _headers, body):
        if result == HTTPRequest.RESULT_SUCCESS and response_code >= 200 and response_code < 300:
            var parsed = JSON.parse_string(body.get_string_from_utf8())
            if typeof(parsed) == TYPE_DICTIONARY:
                var events: Array = parsed.get("events", [])
                if not events.is_empty():
                    var last = events.back()
                    if typeof(last) == TYPE_DICTIONARY:
                        _last_change_timestamp = str(last.get("timestamp", _last_change_timestamp))
                    mother_changes_received.emit(events)
        request.queue_free()
    )
    request.request(url)
