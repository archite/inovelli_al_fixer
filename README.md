# Introduction

When using the Adaptive Lighting integration with Home Assistant along with ZHA groups containing Inoveli switches, turning on the lights via switch will register as manual control.

**Here is an actual use case:**

- Two Blue 2-1 switches on two different circuits.
- Each circuit has two hue bulbs attached.
- Zigbee group created for the four bulbs and the two switches.
- Each switch is bound to the group via LevelControl and OnOff.
- Adaptive Lighting targets Zigbee group.

I've found that even with single bulb/switch setups, it's better to create the group as well and as such, this also  works in that case as well.

# Breaking down the automation:

If the *"Up"* button is pressed, the light will move the adaptive lighting level it should be in and wait to see if been marked as manually controlled and then turn it off. This also will reset a manually controlled light.

If the using *"Double Tap"* in either direction, lights will lower to AL's current minimum brightness or maximum brightness and then set manual control on light.

If *"Triple Tap Up"*, then go to maximum color temperature defined in AL.

# Setup

> This automation requires [Pyscript](https://github.com/custom-components/pyscript) as it allows for mapping group entity back to Inovelli device.

Place **inovelli_al_fixer.py** into `<config_folder>/pyscript/apps/`.

Next, update your HA **configuration.yaml** based on the included sample. For each AL configuration, create a new list item similar to what is shown in example *(my personal configuration)*. Lights that are defined in that AL configuration should be put into the `lights:` array.

That's it!
