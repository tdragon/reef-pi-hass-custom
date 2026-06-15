# Fix MQTT real-time updates for inlet/ATO state (issue #69)

## Overview
- **Problem**: When MQTT is enabled, inlet binary_sensor and ATO state changes from
  reef-pi are not reflected in Home Assistant in real time. Entities only refresh on the
  API poll interval and can appear stale for long periods (the reporter uses ATO/inlet for
  a "bucket low" alert).
- **Root cause (verified against reef-pi controller source)**:
  1. `mqtt_handler._update_device_state()` has no branch for inlet/ATO — such messages are
     dropped (`updated` stays `False`).
  2. `ReefPiMQTTNameMapper.add_ato()` exists but is **never called** by `update_atos()`, so
     the real ATO state topic is never registered → message dropped at the mapper lookup.
  3. `update_inlets()` calls `add_inlet()`, which generates a **phantom** topic
     (`{prefix}/{inlet_name}`) that reef-pi never publishes — inlets can never update via MQTT.
  4. `update_inlets()` is gated on `self.has_ato`, so inlets don't poll without the ATO
     capability.
- **Key fact**: The only real-time MQTT signal for water level is `{prefix}/ato_<name>_state`
  (the 0/1 float-switch reading), emitted by reef-pi on every ATO `Check()`
  (`controller/modules/ato/ato.go:158`). Each ATO references its inlet via the `inlet` field
  (the inlet id). reef-pi emits **nothing** for standalone inlets (inlets are GPIO connectors
  with no telemetry).
- **Benefit**: Inlet/ATO (bucket-low / water-level) state updates in HA in real time via
  MQTT, so alerting and history reflect actual changes immediately.

## Context (from discovery)
- Files/components involved:
  - `custom_components/reef_pi/mqtt_handler.py` — `_update_device_state` (no inlet branch).
  - `custom_components/reef_pi/mqtt_name_mapper.py` — `_generate_topic`, `add_ato`, `add_inlet`.
  - `custom_components/reef_pi/__init__.py` — `update_atos` (no `add_ato` call), `update_inlets`
    (`has_ato` gate + phantom `add_inlet`).
  - `custom_components/reef_pi/sensor.py` — MQTT diagnostic sensors (no inlet/ato entry).
  - `custom_components/reef_pi/binary_sensor.py` — `ReefPiInlet` reads
    `coordinator.inlets[id]["state"]` (unchanged target entity).
- Related patterns found:
  - Equipment MQTT path is the template: `state = bool(int(value))` then
    `coordinator.equipment[id]["state"] = state`.
  - Mapper `_add_device()` does topic generation + collision detection; topics keyed by string.
  - Tests are per-module unit tests using a `MockCoordinator` (`tests/test_mqtt_handler.py`)
    and respx mocks (`tests/async_api_mock.py`).
- Dependencies/facts identified (verified against reef-pi controller source):
  - ATO API object includes `"inlet"` (confirmed in `tests/async_api_mock.py:126` → `"inlet": "2"`).
  - reef-pi has **no** inlet capability flag; `/api/inlets` is always available.
  - `/api/inlets` (`ListInlets`) returns a JSON **list** of inlet objects (`[]gen.Inlet`), so the
    existing `for inlet in inlets: inlet["id"]` iteration is correct.
  - `/api/inlets/{id}/read` (`ReadInlet`) returns a bare **int** 0/1 (`ReadInlet200JSONResponse int`).
    Therefore the polling path (`inlet_raw_value == 1`) and the MQTT path (`bool(int(value))`)
    converge on the same boolean — no change to the polling computation is required.
  - MQTT payload format is `"%f"` (e.g. `"1.000000"`); `int(float(...))` yields 0/1.
  - reef-pi topic for ATO state == mapper's `_generate_topic("ato", name)` →
    `{prefix}/ato_{normalized_name}_state` (verified for several name variants).

## Development Approach
- **Testing approach**: Regular (code first, then tests in the same task).
- Complete each task fully (code + tests passing) before the next.
- Small, focused changes; reuse the existing equipment MQTT pattern.
- **Every task includes new/updated unit tests** (success + error/edge cases).
- **All tests must pass before starting the next task.**
- Maintain backward compatibility (existing temperature/ph/equipment MQTT paths unchanged).
- Run `uv run ruff check --fix`, `uv run ruff format`, and `uv run pyright` as part of verification.

## Testing Strategy
- **Unit tests**: required for every task.
  - `tests/test_mqtt_handler.py` — inlet update branch (on/off, unknown id, tracker recording).
  - `tests/test_mqtt_name_mapper.py` — `add_ato_state` maps ATO topic → `("inlet", inlet_id)`;
    normalization; shared-inlet (no collision) + same-name (collision) behavior; macro ATO with empty
    `inlet` is skipped; phantom inlet topic removed.
  - `tests/test_sensors.py` (+ `tests/async_api_mock.py`) — inlets populate when `has_ato` is False
    (decoupling), using a new non-empty `/api/inlets` mock and an `ato`-absent capabilities variant.
  - `tests/test_mqtt_sensors.py` — inlet MQTT diagnostic sensor created (exact name
    "MQTT Last Inlet Update") and reflects tracker.
  - Convergence is already guaranteed by reef-pi returning int 0/1 for `/read` (see Context), so no
    separate MQTT-vs-polling reconciliation test is needed; the handler on/off tests cover the mapping.
- **E2E tests**: none in this project (no UI e2e harness) — N/A.

## Progress Tracking
- Mark completed items `[x]` immediately when done.
- Add newly discovered tasks with ➕ prefix; blockers with ⚠️ prefix.
- Keep this file in sync with actual work.

## Solution Overview
- **Resolve ATO → inlet at registration time, not message time.** When polling ATOs, register
  the ATO's state topic (`ato_<name>_state`) mapped to its **inlet id** with device_type
  `"inlet"`. The MQTT handler then needs only a generic `"inlet"` branch that writes
  `coordinator.inlets[inlet_id]["state"]` — updating the existing inlet binary_sensor the user
  already has.
- This reuses the existing entity and polling path; MQTT just adds the real-time update. The
  value is identical to what polling computes (both derive from the inlet read), so there is no
  divergence between MQTT and polling.
- Remove the phantom `add_inlet` registration. Standalone inlets (not tied to an ATO) remain
  poll-only because reef-pi publishes no telemetry for them — documented as a known limitation.
- Decouple inlet polling from `has_ato` so inlet binary_sensors exist/refresh regardless of the
  ATO capability.

## Technical Details
- **Handler** (`_update_device_state`): add, mirroring the equipment branch:
  ```python
  elif device_type == "inlet":
      if device_id in self.coordinator.inlets:
          state = bool(int(value))
          self.coordinator.inlets[device_id]["state"] = state
          updated = True
  ```
  Tracker recording happens via the existing `record_mqtt_update(device_type, device_id)` with
  `device_type == "inlet"`.
- **Mapper**: allow generating a topic with a pattern different from the stored device_type.
  - Extend `_add_device(device_type, name, device_id, topic_type=None)` →
    `topic = self._generate_topic(topic_type or device_type, name)`.
  - Add `add_ato_state(ato_name, inlet_id)` →
    `self._add_device("inlet", ato_name, inlet_id, topic_type="ato")`.
  - Remove `add_inlet` (and its phantom path). `add_ato` becomes unused → remove to avoid dead
    code (keep the `"ato"` case in `_generate_topic`; it is used as `topic_type`). Keep the
    `"inlet"` label in `notify_collisions` type_names.
  - Note: after this change no device is stored with `device_type == "ato"`, so the `"ato"` entry
    in `notify_collisions` `type_names` becomes unreachable — leave it (harmless) rather than
    "fixing" the live `"inlet"` label. Collisions between two same-named ATOs will be reported
    under the "Inlet" label by inlet id; acceptable (the message still lists the conflicting topic).
- **`update_atos`**: inside the existing per-ATO loop, register the state topic:
  ```python
  inlet_id = atos[id].get("inlet")
  if inlet_id:
      self.mqtt_name_mapper.add_ato_state(atos[id]["name"], inlet_id)
  ```
  Guard skips macro-based ATOs (`is_macro` → empty `inlet`).
- **`update_inlets`**: remove `self.mqtt_name_mapper.add_inlet(...)`; change the `if self.has_ato:`
  gate so inlets poll unconditionally (rely on the existing `if inlets:` guard for empty results).
  `/api/inlets` returns a list, so `for inlet in inlets: inlet["id"]` is unchanged and correct.
  Deliberate tradeoff: ATO-less installs now issue one extra `/api/inlets` GET per poll cycle; the
  `if inlets:` guard skips the per-inlet `read` calls when the list is empty, so the marginal cost
  is a single list GET.
- **Diagnostics** (`sensor.py`): add `ReefPiMQTTLastUpdateSensor(coordinator, "inlet")` →
  "MQTT Last Inlet Update" (queries tracker under the `"inlet"` device_type used above).
- **Processing flow** (after fix):
  `reef-pi ATO Check → publish {prefix}/ato_<name>_state` → wildcard subscription →
  `_mqtt_message_received` → mapper lookup returns `("inlet", inlet_id)` →
  `_update_device_state("inlet", inlet_id, value)` → `coordinator.inlets[inlet_id]["state"]` →
  `async_set_updated_data` → inlet binary_sensor re-renders.

## What Goes Where
- **Implementation Steps** (checkboxes): all code + unit tests + docs in this repo.
- **Post-Completion** (no checkboxes): manual verification on a live reef-pi with MQTT, and
  the GitHub issue response.

## Implementation Steps

### Task 1: Add `inlet` branch to the MQTT handler

**Files:**
- Modify: `custom_components/reef_pi/mqtt_handler.py`
- Modify: `tests/test_mqtt_handler.py`

- [x] add an `elif device_type == "inlet":` branch in `_update_device_state` that sets
      `coordinator.inlets[device_id]["state"] = bool(int(value))` and `updated = True`
      (guard `device_id in self.coordinator.inlets`), with a debug log
- [x] confirm the existing tracker recording + `async_set_updated_data` path covers `"inlet"`
      (no extra change expected)
- [x] extend `MockCoordinator` in `tests/test_mqtt_handler.py` with `self.inlets = {"2": {"state": False}}`
      and register `reef-pi/ato_test_ato_state → ("inlet", "2")` — the hand-registered topic string
      must equal `_generate_topic("ato", "Test ATO")` so Task 1 and Task 2 assert the same topic
- [x] write test: inlet state goes True on payload `"1.000000"` and `async_set_updated_data` called
- [x] write test: inlet state goes False on payload `"0.000000"`
- [x] write test: unknown inlet id is a no-op (no update, no crash)
- [x] run tests — must pass before Task 2

### Task 2: Register ATO-state → inlet mapping; drop the phantom inlet topic

**Files:**
- Modify: `custom_components/reef_pi/mqtt_name_mapper.py`
- Modify: `custom_components/reef_pi/__init__.py`
- Modify: `tests/test_mqtt_name_mapper.py`

- [x] extend `_add_device` with optional `topic_type=None`; generate topic via
      `self._generate_topic(topic_type or device_type, name)`
- [x] add `add_ato_state(self, ato_name, inlet_id)` →
      `self._add_device("inlet", ato_name, inlet_id, topic_type="ato")`
- [x] remove `add_inlet` and `add_ato` methods (dead after this change); keep the `"ato"` case in
      `_generate_topic` and the `"inlet"` label in `notify_collisions`
- [x] in `__init__.py update_atos`, register `add_ato_state(atos[id]["name"], inlet_id)` only when
      `inlet_id = atos[id].get("inlet")` is truthy (skips macro-based ATOs with empty `inlet`)
- [x] in `__init__.py update_inlets`, remove the `self.mqtt_name_mapper.add_inlet(...)` call
- [x] write test: `add_ato_state("Test ATO", "2")` registers `reef-pi/ato_test_ato_state → ("inlet", "2")`
- [x] write test: name normalization (e.g. `"My-ATO"`) produces the expected topic
- [x] write test: two ATOs sharing one inlet (different names) both map to `("inlet", id)` without a
      collision; re-registration is idempotent
- [x] write test: two ATOs with the **same** normalized name but different inlets trigger collision
      detection (topic disabled) — proves collision detection still fires through the `topic_type` path
- [x] write test: `update_atos` does not call `add_ato_state` for a macro-based ATO with empty `inlet`
- [x] run tests — must pass before Task 3

### Task 3: Decouple inlet polling from `has_ato`

**Files:**
- Modify: `custom_components/reef_pi/__init__.py`
- Modify: `tests/async_api_mock.py`
- Modify: `tests/test_sensors.py`

- [x] change `update_inlets` so it no longer requires `self.has_ato` (poll `/api/inlets`
      unconditionally; keep the existing `if inlets:` guard for empty results)
- [x] verify `binary_sensor.async_setup_entry` still builds entities from `coordinator.inlets`
- [x] in `tests/async_api_mock.py`, add a non-empty `/api/inlets` payload (list incl. inlet id `"2"`)
      + matching `/api/inlets/{id}/read` (int `1`); current `mock_all` returns `{}` so the loop is
      never exercised. Add an `ato`-absent capabilities variant (current `mock_capabilities` always
      sets `ato: True`)
- [x] write test: with capabilities where `ato` is absent but `/api/inlets` returns inlets,
      `coordinator.inlets` is populated (and the inlet binary_sensor entity is created)
- [x] write/adjust test: existing inlet polling behavior still holds when `ato` is present
- [x] run tests — must pass before Task 4

### Task 4: Add the inlet MQTT diagnostic sensor

**Files:**
- Modify: `custom_components/reef_pi/sensor.py`
- Modify: `tests/test_mqtt_sensors.py`

- [x] add `ReefPiMQTTLastUpdateSensor(coordinator, "inlet")` to the `diagnostic_sensors` list
- [x] write test: the inlet diagnostic sensor is created when MQTT is enabled with name
      "MQTT Last Inlet Update" (`.title()` of `"inlet"`)
- [x] write test: it returns the tracker's last `"inlet"` update timestamp after an inlet MQTT update
- [x] run tests — must pass before Task 5

### Task 5: Verify acceptance criteria
- [x] verify the end-to-end flow logic: `ato_<name>_state` → inlet binary_sensor updates (covered by
      Task 1 + Task 2 unit tests) — Task 1 `tests/test_mqtt_handler.py`
      (`test_mqtt_message_received_inlet_on/off`, `test_update_device_state_unknown_inlet`) +
      Task 2 `tests/test_mqtt_name_mapper.py` (`test_add_ato_state_maps_to_inlet`,
      `test_update_atos_registers_ato_state`); both assert the same topic string
      `reef-pi/ato_test_ato_state` == `_generate_topic("ato", "Test ATO")` → `("inlet", "2")`
- [x] verify standalone inlets and macro-based ATOs are handled (no crash, no phantom topic) —
      macro ATO skip: `test_update_atos_skips_macro_ato` (empty `inlet` → no `add_ato_state`, empty
      `topic_to_device`); standalone inlet (no ATO): `test_inlet_polled_without_ato` (inlets populate
      with `has_ato=False`); `update_inlets` no longer calls `add_inlet` so no phantom topic
- [x] run full suite: `uv run pytest` — 91 passed
- [x] run `uv run ruff check --fix` and `uv run ruff format` — clean (All checks passed!; 28 files unchanged)
- [x] run `uv run pyright` — no new errors (changed files: 0 errors / 9 warnings on both master
      baseline and this branch — identical pre-existing `unique_id` CoordinatorEntity warnings in
      sensor.py; no new errors/warnings introduced)

### Task 6: [Final] Update documentation
- [x] update `CLAUDE.md` MQTT section: ATO `_state` drives the inlet binary_sensor in real time;
      inlet polling decoupled from `has_ato`; standalone inlets remain poll-only (reef-pi limitation);
      add "MQTT Last Inlet Update" diagnostic sensor to the list
- [x] move this plan to `docs/plans/completed/`

## Post-Completion
*Items requiring manual intervention or external systems — informational only*

**Manual verification:**
- On a live reef-pi with MQTT enabled and an ATO/float-switch: trigger a bucket-low / water-level
  change and confirm the HA inlet binary_sensor flips within the ATO `period` (seconds), not the
  poll interval. Confirm "MQTT Last Inlet Update" advances and "MQTT Messages Received" increments.

**Issue response:**
- Comment on GitHub issue #69 summarizing the root cause and the fix once released.
