import time
import vgamepad as vg

gamepad = vg.VX360Gamepad()

for i in range(60):
    time.sleep(1)
    print(f"{30-(i+1)}")
# Press SELECT (Back) + X (A button in Xbox mapping)
gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK)
gamepad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_A)

gamepad.update()

time.sleep(2)

# Release buttons
gamepad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK)
gamepad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_A)

gamepad.update()

time.sleep(50)