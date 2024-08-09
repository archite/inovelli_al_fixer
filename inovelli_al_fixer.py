# Copyright 2024 Adam Karim
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the “Software”), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import logging

# Default values for trigger matching
cluster = 64561
endpoint = 2
dim_commands = [
    "button_1_hold",
    "button_2_hold",
]
level_commands = [
    "button_1_double",
    "button_2_double",
    "button_2_triple",
]
on_commands = [
    "button_2_press",
]
commands = dim_commands + level_commands + on_commands
inovelli_models = [
    "DZM32-SN",
    "VZM31-SN",
    "VZW35-SN",
]


registered_triggers = []


def make_inovelli_al_fixer(
    *, lights: str, al_switch: str, al_sleep_switch: str
) -> None:
    for light_entity in lights:
        # Add prefix to log messages to make easier to trace
        def mklog(msg: str, level: str = "debug") -> None:
            logger = getattr(log.info, "__self__")
            level = getattr(logging, level.upper(), logger.getEffectiveLevel())
            logger.log(level, f"{light_entity}: {msg}")

        # Find group entity and fail if not found
        entity = hass.data["zha"].gateway_proxy.get_entity_reference(light_entity)

        if not entity:
            mklog("Entity not found!", "error")
            return

        if not entity.entity_data.group_proxy:
            mklog("Entity is not a group!", "error")
            return

        # Get group object for light
        group = entity.entity_data.group_proxy.group

        # Find Inovelli switches in group and fail if not found
        switches = [
            str(member.device.ieee)
            for member in group.members
            if member.device.manufacturer == "Inovelli"
            and member.device.model in inovelli_models
        ]

        if not switches:
            mklog("No Inovelli switches found in group!", "error")
            return

        trigger = [
            f"cluster_id == {cluster}",
            f"command in {commands}",
            f"device_ieee in {switches}",
            f"endpoint_id == {endpoint}",
        ]

        # Manage light based on command
        def light_on(light_entity: str, command: str) -> None:
            al_attr = state.getattr(al_switch)
            mklog("setting light on")
            light.turn_on(
                brightness_pct=al_attr["brightness_pct"]
                if command == "button_2_press"
                else al_attr["configuration"][
                    "sleep_brightness"
                    if hass.states.is_state(al_sleep_switch, "on")
                    else "min_brightness"
                ]
                if command == "button_1_double"
                else al_attr["configuration"]["max_brightness"],
                entity_id=light_entity,
                kelvin=al_attr["configuration"]["max_color_temp"]
                if command == "button_2_triple"
                else al_attr["color_temp_kelvin"],
                transition=al_attr["configuration"]["initial_transition"],
            )

        # Set manual control as needed
        def manual_control(light_entity: str, enabled: str) -> None:
            mklog("setting manual control " + ("on" if enabled else "off"))
            adaptive_lighting.set_manual_control(
                entity_id=al_switch,
                lights=[light_entity],
                manual_control=enabled,
            )

        @event_trigger("zha_event", " and ".join(trigger))
        @task_unique(f"inovelli_al_fixer_{light_entity}")
        def inovelli_event(
            light_entity: str = light_entity, command: str | None = None, **kwargs
        ) -> None:
            mklog(f"{command} pressed")

            # Turn on light to double tap level and set manual control
            if command in level_commands:
                manual_control(light_entity, True)
                light_on(light_entity, command)

            # Turn on/restore without manual control on
            if command in on_commands:
                light_on(light_entity, command)
                mklog("waiting for light in manual_control")
                trig_info = task.wait_until(
                    state_trigger=f"'{light_entity}' in {al_switch}.manual_control",
                    timeout=60,
                )
                if trig_info["trigger_type"] == "state":
                    manual_control(light_entity, False)

            # Turn manual control on hold
            if command in dim_commands:
                manual_control(light_entity, True)

        registered_triggers.append(inovelli_event)


@time_trigger("startup")
def inovelli_al_fixer_startup() -> None:
    for app in pyscript.app_config:
        make_inovelli_al_fixer(**app)
