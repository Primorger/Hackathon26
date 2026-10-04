from machine import Pin, ADC, I2C, UART
import time
import ssd1306
import framebuf
import math
import _thread

# ==========================================
# WEB DASHBOARD CONFIG (ESP32-C3 via ESP-AT)
# ==========================================
# UART to the onboard ESP32-C3. The older Challenger RP2040 WiFi used UART1 on GP4/GP5;
# CHECK the MkII pinout diagram and change these if they differ.
UART_ID, TX_PIN, RX_PIN, BAUD = 1, 4, 5, 115200
DEBUG = True   # print ESP32-C3 traffic + send results to the REPL (set False when it works)
AP_SSID, AP_PASS = "CloudTracker", "energy2026"   # password must be 8+ chars
CONTROL_PIN = "1234"                              # needed for the Recalibrate button
PRINT_SENSORS = False                             # True = your 250 ms voltage printout in the REPL
HIST_LEN = 120                                    # chart points (one per 250 ms = 30 s)

adc_pins = {
    "TL (A0)": ADC(Pin(26)),
    "TR (A1)": ADC(Pin(27)),
    "BL (A2)": ADC(Pin(28)),
    "BR (A3)": ADC(Pin(29))
}

conversion_factor = 6.6 / 65535

i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=400000)
oled = ssd1306.SSD1306_I2C(128, 32, i2c)

PANEL_WIDTH_M = 0.070  
PANEL_HEIGHT_M = 0.055 

# ==========================================
# SPRITES
# ==========================================
arrow_n  = bytearray([0x01, 0x80, 0x03, 0xC0, 0x07, 0xE0, 0x0F, 0xF0, 0x1F, 0xF8, 0x3F, 0xFC, 0x7F, 0xFE, 0x03, 0xC0, 0x03, 0xC0, 0x03, 0xC0, 0x03, 0xC0, 0x03, 0xC0, 0x03, 0xC0, 0x03, 0xC0, 0x03, 0xC0, 0x03, 0xC0])
arrow_s  = bytearray([0x03, 0xC0, 0x03, 0xC0, 0x03, 0xC0, 0x03, 0xC0, 0x03, 0xC0, 0x03, 0xC0, 0x03, 0xC0, 0x03, 0xC0, 0x03, 0xC0, 0x7F, 0xFE, 0x3F, 0xFC, 0x1F, 0xF8, 0x0F, 0xF0, 0x07, 0xE0, 0x03, 0xC0, 0x01, 0x80])
arrow_e  = bytearray([0x00, 0x00, 0x00, 0x40, 0x00, 0x60, 0x00, 0x70, 0x00, 0x78, 0x00, 0x7C, 0xFF, 0xFE, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFE, 0x00, 0x7C, 0x00, 0x78, 0x00, 0x70, 0x00, 0x60, 0x00, 0x40, 0x00, 0x00])
arrow_w  = bytearray([0x00, 0x00, 0x02, 0x00, 0x06, 0x00, 0x0E, .1'
b'0x00, 0x1E, 0x00, 0x3E, 0x00, 0x7F, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x7F, 0xFF, 0x3E, 0x00, 0x1E, 0x00, 0x0E, 0x00, 0x06, 0x00, 0x02, 0x00, 0x00, 0x00])
arrow_ne = bytearray([0x00, 0xFF, 0x00, 0x7F, 0x00, 0x3F, 0x00, 0x1F, 0x00, 0x3F, 0x00, 0x77, 0x00, 0xE3, 0x01, 0ESP>x Cb1',
 
0OxK0
3
,
 
0>x'8
0, 0x07, 0x00, 0x0E, 0x00, 0x1C, 0x00, 0x38, 0x00, 0x70, 0x00, 0xE0, 0x00, 0xC0, 0x00])
arrow_nw = bytearray([0xFF, 0x00, 0xFE, 0x00, 0xFC, 0x00, 0xF8, 0x00, 0xFC, 0x00, 0xEE, 0x00, 0xC7, 0x00, 0x83, 0x80, 0x01, 0xC0, 0x00, 0xE0, 0x00, 0x70, 0x00, 0x38, 0x00, 0x1C, 0x00, 0x0E, 0x00, 0x07, 0x00, 0x03])
arrow_se = bytearray([0xC0, 0x00, 0xE0, 0x00, 0x70, 0x00, 0x38, 0x00, ESP>0 xb1'C
,
 R0exc0v0 ,2 506x 0bEy,t e0sx
0
0',
 0x07, 0x00, 0x03, 0x80, 0x01, 0xC1, 0x00, 0xE3, 0x00, 0x77, 0x00, 0x3F, 0x00, 0x1F, 0x00, 0x3F, 0x00, 0x7F, 0x00, 0xFF])
arrow_sw = bytearray([0x00, 0x03, 0x00, 0x07, 0x00, 0x0E, 0x00, 0x1C, 0x00, 0x38, 0x00, 0x70, 0x00, 0xE0, 0x01, 0xC0, 0x83, 0x80, 0xC7, 0x00, 0xEE, 0x00, 0xFC, 0x00, 0xF8, 0x00, 0xFC, 0x00, 0xFE, 0x00, 0xFF, 0x00])
stable_i = bytearray([0x00, 0x00, 0x3F, 0xFC, 0x3F, 0xFC, 0x30, 0x0C, 0x30, 0x0C, 0x30, 0x0C, 0x30, 0x0C, 0x30, 0x0C, 0x30, 0x0C, 0x30, 0x0C, 0x30, 0x0C, 0x30, 0x0C, 0x3F, 0xFC, 0x3F, 0xFC, 0x00, 0x00, 0x00, 0x00])

def make_buffer(b_arr):
    return framebuf.FrameBuffer(b_arr, 16, 16, framebuf.MONO_HLSB)

sprites = {
    "E": make_buffer(arrow_e), "W": make_buffer(arrow_w), 
    "N": make_buffer(arrow_n), "S": make_buffer(arrow_s),
    "NE": make_buffer(arrow_ne), "NW": make_buffer(arrow_nw), 
    "SE": make_buffer(arrow_se), "SW": make_buffer(arrow_sw),
    "STABLE": make_buffer(stable_i)
}

OPPOSITE_DIRECTIONS = {
    "N": "S", "S": "N", "E": "W", "W": "E",
    "NE": "SW", "SW": "NE", "NW": "SE", "SE": "NW",
    "STABLE": "STABLE"
}

last_voltages = {label: 0.0 for label in adc_pins}
baselines = {label: 0.0 for label in adc_pins}
stability_threshold = 0.03
vector_sensitivity = 0.20  

graph_history = []
max_graph_points = 58

cloud_active = False       
last_valid_direction = "STABLE" 

Recv 75 bytes

SEND OK
'
b'
held_entry_speed = 0.00
trailing_lock_active = False    
lock_timer = 0                  

stability_sample_counter = 0
previous_loop_voltages = {label: 0.0 for label in adc_pins}

active_vector = "STABLE"
calculated_speed = 0.00

# =====================ESP>= =b='=0=,=C=L=O=S=E=D=
=
=
=
=E=R=R=O=R=


'#
 SHARED STATE (core 0 writes, web server on core 1 reads)
# ==========================================
state = {"v": [0.0] * 4, "b": [0.0] * 4, "vec": "STABLE", "spd": 0.0,
         "cloud": 0, "lock": 0, "hist": [], "ev": [], "recal": 0}

def log(msg):
    print(msg)
    state["ev"].append("%ds %s" % (time.ticks_ms() // 1000, msg.replace('"', "'")))
    if len(state["ev"]) > 6:
        state["ev"].pop(0)

# ==========================================
# ESP32-C3 (ESP-AT) WEB SERVER  - runs on core 1
# ==========================================
uart = UART(UART_ID, baudrate=BAUD, tx=Pin(TX_PIN), rx=Pin(RX_PIN), rxbuf=4096, txbuf=2048)
rx = b""

def pump():
    global rx
    d = uart.read()
    if d:
        rx += d
        if DEBUG:
            print("ESP>", d[:70])
        if len(rx) > 6000 and b"+IPD," not in rx:
            rx = rx[-256:]

def wait_for(token, timeout=2000):
    global rx
    t0 = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), t0) < timeout:
        pump()
        i = rx.find(token)
        if i >= 0:
            rx = rx[:i] + rx[i + len(token):]
            return True
        time.sleep_ms(2)
    return False

def at(cmd, expect=b"OK", timeout=2000):
    pump()
    uart.write(cmd + "\r\n")
    ok = wait_for(expect, timeout)
    if not ok:
        print("AT fail:", cmd)
    return ok

ESP_RST_PIN = 19     # GPIO19 -> ESP32-C3 reset (active low), per the MkII datasheet
BAUDS = (115200, 1000000, 921600, 460800, 230400, 57600, 9600)   # tried in order

def esp_reset():
    """Hardware-reset the ESP32-C3 so it boots into ESP-AT cleanly."""
    global rx
    r = Pin(ESP_RST_PIN, Pin.OUT, value=0)
    time.sleep_ms(100)
    r.value(1)
    time.sleep_ms(2000)
    uart.read()
    rx = b""

def esp_probe():
    """Find the baud rate the ESP-AT firmware answers on."""
    global rx
    for b in BAUDS:
        uart.init(baudrate=b, tx=Pin(TX_PIN), rx=Pin(RX_PIN), rxbuf=4096, txbuf=2048)
        uart.read()
        rx = b""
        for _ in range(3):
            uart.write("AT\r\n")
            if wait_for(b"OK", 400):
                print("ESP-AT answered at", b, "baud")
                return b
    return None

def esp_start():
    esp_reset()
    if esp_probe() is None:
        print("No reply from ESP32-C3 - check UART pins (GP4/GP5), reset pin (GP19), power")
        return False
    at("ATE0")
    at("AT+CWMODE=2")
    at('AT+CWSAP="%s","%s",5,3,4' % (AP_SSID, AP_PASS))
    at("AT+CIPMUX=1")
    at("AT+CIPSERVER=1,80")
    print("Dashboard up -> http://192.168.4.1")
    return True

TX_CHUNK = 256   # bytes per AT+CIPSEND (small chunks are the most reliable on this UART link)

def write_all(data):
    """uart.write() can return short; keep writing until every byte is queued."""
    if isinstance(data, str):
        data = data.encode()
    mv = memoryview(data)
    t0 = time.ticks_ms()
    while len(mv) and time.ticks_diff(time.ticks_ms(), t0) < 2000:
        n = uart.write(mv)
        if n:
            mv = mv[n:]
        else:
            time.sleep_ms(1)
    return len(mv) == 0

def send(link, body, ctype="text/html", code="200 OK"):
    if isinstance(body, str):
        body = body.encode()
    head = ("HTTP/1.1 %s\r\nContent-Type: %s\r\nContent-Length: %d\r\n"
            "Cache-Control: no-store\r\nConnection: close\r\n\r\n" % (code, ctype, len(body)))
    data = head.encode() + body
    for i in range(0, len(data), TX_CHUNK):
        chunk = data[i:i + TX_CHUNK]
        if not write_all("AT+CIPSEND=%d,%d\r\n" % (link, len(chunk))):
            return
        if not wait_for(b">", 1500):
            print("TX no prompt: link", link, "chunk", i // TX_CHUNK, rx[-70:])
            return
        if not write_all(chunk):
            print("TX short write: link", link, "chunk", i // TX_CHUNK)
            return
        if not wait_for(b"SEND OK", 2500):
            print("TX no SEND OK: link", link, "chunk", i // TX_CHUNK, rx[-70:])
            return
    if DEBUG:
        print("TX done: link", link, len(data), "bytes")
    uart.write("AT+CIPCLOSE=%d\r\n" % link)

def to_json():
    s = state
    return ('{"v":[%s],"b":[%s],"vec":"%s","spd":%.2f,"cloud":%d,"lock":%d,"up":%d,'
            '"hist":[%s],"ev":[%s]}' % (
                ",".join(str(int(x * 1000)) for x in s["v"]),
                ",".join(str(int(x * 1000)) for x in s["b"]),
                s["vec"], s["spd"], s["cloud"], s["lock"], time.ticks_ms() // 1000,
                ",".join(str(x) for x in s["hist"]),
                ",".join('"%s"' % e for e in s["ev"])))

def qs(q):
    out = {}
    for p in q.split("&"):
        if "=" in p:
            k, v = p.split("=", 1)
            out[k] = v
    return out

def handle(link, payload):
    try:
        path = payload.split(b"\r\n")[0].split()[1].decode()
    except Exception:
        send(link, "bad request", "text/plain", "400 Bad Request")
        return
    route, _, q = path.partition("?")
    if route == "/":
        send(link, PAGE)
    elif route == "/api":
        send(link, to_json(), "application/json")
    elif route == "/set":
        p = qs(q)
        if p.get("pin") != CONTROL_PIN:
            send(link, '{"err":"pin"}', "application/json", "403 Forbidden")
            return
        if p.get("k") == "recal":
            state["recal"] = 1
        send(link, to_json(), "application/json")
    else:
        send(link, "not found", "text/plain", "404 Not Found")

def poll_http():
    global rx
    pump()
    while True:
        i = rx.find(b"+IPD,")
        if i < 0:
            return
        j = rx.find(b":", i)
        if j < 0:
            return
        try:
            head = rx[i + 5:j].split(b",")
            lin'
OK

>'
b'k, n = int(head[0]), int(head[1])
        except Exception:
            rx = rx[:i] + rx[j + 1:]
            continue
        if len(rx) < j + 1 + n:
            return
        payload = rx[j + 1:j + 1 + n]
        rx = rx[:i] + rx[j + 1 + n:]
        if DEBUG:
            print("REQ link", link, payload.split(b"\r\n")[0])
        handle(link, payload)

def web_main():
    while not esp_start():
        time.sleep(2)
    while True:
        poll_http()
        time.sleep_ms(5)

PAGE = b"""<!doctype html><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1"><title>Cloud Tracker</title>
<style>
:root{--bg:#0b1ESP>2 2b0';
-
-OcKd
:
#
1
3>1'c
2e;--fg:#e6edf7;--mu:#7d8aa3;--ok:#2dd4bf;--wa:#f59e0b;--bd:#f43f5e}
*{box-sizing:border-box}
body{margin:0 auto;max-width:760px;padding:14px;background:var(--bg);color:var(--fg);font:15px system-ui,sans-serif}
h1{font-size:18px;margin:0 0 12px;display:flex;align-items:center;gap:8px}
#dot{width:10px;height:10px;border-radius:50%;background:var(--mu)}#up{margin-left:auto;color:var(--mu);font-size:13px}
.c{background:var(--cd);border-radius:12px;padding:12px;margin-bottom:10px}
.c small{color:var(--mu);display:block;margin-bottom:4px}
.r{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.v{font-size:30px;font-weight:700}.v i{font-size:14px;color:var(--mu);font-style:normal;font-weight:400}
#st{display:inline-block;padding:4px 12px;border-radius:99px;font-weight:700;font-size:14px;background:#1e2a44}
#cmp{display:flex;align-items:P> b'
SEND OK
'
b'center;gap:16px}
#arr{width:84px;height:84px;fill:var(--ok);transition:transform .4s}#arr.off{fill:var(--mu);opacity:.5}
.p{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.pn{background:#0f1729;border-radius:10px;padding:10px}
.pn b{font-size:20px}.pn span{font-size:12px;color:var(--mu);display:block}
.bar{height:6px;background:#1e2a44;border-radius:4px;margin-top:6px;overflow:hidden}.bar div{height:100%;background:var(--ok);transition:width .3s}
canvas{width:100%;height:110px;display:block}
#evP> b'
Recv 75 bytes

SEND OK
'
b' div{font:12px ui-monospace,monospace;color:var(--mu);padding:2px 0}
button{width:100%;padding:12px;border:0;border-radius:10px;background:#1e2a44;color:var(--fg);font:600 14px system-ui}
</style>
<h1><span id=dot></span>Cloud Tracker<span id=up>0s</spaP> b'0,CLOSED

ERROR
'
b'n></h1>
<div class=c><div id=cmp>
<svg id=arr class=off viewBox="0 0 24 24"><path d="M12 2l8 9h-5v11H9V11H4z"/></svg>
<div><small>Cloud shadow</small><div class=v><span id=sp>0.00</span> <i>m/s</i></div>
<div><span id=st>CLEAR</span> <span id=dr style="color:var(--mu);margin-left:8px">-</span></div></div></div></div>
<div class=c><small>Panels (voltage vs. calibrated baseline)</small><div class=p id=pn></div></div>
<div class=c><small>Average panel voltage, last 30 s</small><canvas id=cv width=700 height=220></canvas></div>
<div class=c id=ev><small>Events</small></div>
<button onclick=rc()>Recalibrate (use in clear, steady light)</button>
<script>
const $=i=>document.getElementById(i),N=['TL (A0)','TR (A1)','BL (A2)','BR (A3)'],
D={N:0,NE:45,E:90,SE:135,S:180,SW:225,W:270,NW:315};
$('pn').innerHTML=N.map((n,i)=>`<div class=pn><span>${n}</span><b id=v${i}>-</b> <span id=d${i} style=display:inline></span><div class=bar><div id=b${i}></div></div></div>`).join('');
async function api(u){const r=await fetch(u);if(r.status==403)throw 403;return r.json()}
async function rc(){let p=localStorage.p||prompt('Control PIN');if(!p)return;localStorage.p=p;
 try{await api('/set?k=recal&pin='+p)}catch(e){localStorage.p='';alert('Wrong PIN')}}
function draw(s){
 $('up').textContent=s.up+'s';$('sp').textContent=s.spd.toFixed(2);
 const st=$('st'),a=$('arr'),c=s.cloud?'CLOUD OVERHEAD':s.lock?'TRAILING EDGE':s.vec=='STABLE'?'CLEAR':'SHADOW MOVING';
 st.textContent=c;st.style.background=s.cloud?'var(--bd)':s.lock?'var(--wa)':'#1e2a44';
 $('dr').textContent=s.vec=='STABLE'?'':'heading '+s.vec;
 if(s.vec!='STABLE'){a.setAttribute('class','');a.style.transform='rotate('+D[s.vec]+'deg)'}else a.setAttribute('class','off');
 s.v.forEach((v,i)=>{$('v'+i).textContent=(v/1000).toFixed(2)+' V';const d=v-s.b[i];
  $('d'+i).textContent=(d>=0?'+':'')+(d/1000).toFixed(2);$('d'+i).style.color=d<-350?'var(--bd)':'var(--mu)';
  $('b'+i).style.width=Math.min(100,v/33)+'%'});
 spark(s.hist);
 $('ev').innerHTML='<small>Events</small>'+s.ev.slice().reverse().map(e=>'<div>'+e+'</div>').join('')}
function spark(h){const c=$('cv'),x=c.getContext('2d'),W=c.width,H=c.height;x.clearRect(0,0,W,H);if(h.length<2)return;
 const hi=Math.max(...h)*1.1||1;x.strokeStyle='#2dd4bf';x.lineWidth=3;x.beginPath();
 h.forEach((v,i)=>{const px=i*W/(h.length-1),py=H-v/hi*H;i?x.lineTo(px,py):x.moveTo(px,py)});x.stroke();
 x.lineTo(W,H);x.lineTo(0,H);x.fillStyle='rgba(45,212,191,.15)';x.fill();
 x.fillStyle='#7d8aa3';x.font='20px sans-serif';x.fillText((hi/1000).toFixed(2)+' V',6,22)}
async function tick(){try{draw(await api('/api'));$('dot').style.background='var(--ok)'}catch(e){$('dot').style.background='var(--bd)'}}
tick();setInterval(tick,1000);
</script>"""

# ==========================================
# SENSING
# ==========================================
def read_oversampled(adc_channel):
    total = 0
    for _ in range(16):
        total += adc_channel.read_u16()
    return total / 16

def calibrate():
    global baselines, cloud_active, trailing_lock_active, last_valid_direction
    global held_entry_speed, active_vector, calculated_speed
    oled.fill(0)
    oled.text("CALIBRATING...", 2, 12)
    oled.show()
    new_b = {label: 0.0 for label in adc_pins}
    for _ in range(4):
        for label, channel in adc_pins.items():
            new_b[label] += (read_oversampled(channel) * conversion_factor) / 4
        time.sleep(0.5)
    baselines = new_b
    cloud_active = False
    trailing_lock_active = False
    last_valid_direction = "STABLE"
    held_entry_speed = 0.00
    active_vector = "STABLE"
    calculated_speed = 0.00
    oled.fill(0)
    oled.text("CALIBRATION DONE", 2, 12)
    oled.show()
    time.sleep(1.0)
    log("Calibrated")

# Start the web server on the second core so OLED/sensing never stall on WiFi traffic
_thread.start_new_thread(web_main, ())

calibrate()

last_graph_tick = time.ticks_ms()
last_vector_tick = time.ticks_ms()

# ==========================================
# MAIN LOOP
# ==========================================

while True:
    current_time = time.ticks_ms()

    if state["recal"]:
        state["recal"] = 0
        calibrate()
        current_time = time.ticks_ms()
        last_graph_tick = current_time
        last_vector_tick = current_time
    
    if time.ticks_diff(current_time, last_graph_tick) >= 50:
        last_graph_tick = current_time
        current_voltages = {}
        
        for label, adc_channel in adc_pins.items():
            raw_average = read_oversampled(adc_channel)
            measured_voltage = raw_average * conversion_factor
            
            if measured_voltage < 0.05:
                measured_voltage = 0.0
                
            if abs(measured_voltage - last_voltages[label]) >= stability_threshold:
                last_voltages[label] = measured_voltage
            
            current_voltages[label] = last_voltages[label]

        system_avg_voltage = sum(current_voltages.values()) / 4
        graph_history.append(system_avg_voltage)
        if len(graph_history) > max_graph_points:
            graph_history.pop(0)
            
        oled.fill(0) 
        oled.blit(sprites[active_vector], 0, 8)
        oled.text(f"{calculated_speed:.2f}", 18, 4)
        oled.text("m/s", 18, 18)
        oled.vline(66, 0, 32, 1)
        
        for idx, sample_voltage in enumerate(graph_history):
            x_pixel = 68 + idx
            y_pixel = int(30 - (sample_voltage * 5.6))
            y_safe = max(2, min(y_pixel, 30))
            oled.pixel(x_pixel, y_safe, 1)

        oled.show()

    if time.ticks_diff(current_time, last_vector_tick) >= 250:
        last_vector_tick = current_time
        
        if 'current_voltages' in locals() and len(current_voltages) == 4:
            output_strings = [f"{k}: {current_voltages[k]:.2f}V" for k in adc_pins]
            if PRINT_SENSORS:
                print(" | ".join(output_strings))
            
            v_tl = current_voltages["TL (A0)"]
            v_tr = current_voltages["TR (A1)"]
            v_bl = current_voltages["BL (A2)"]
            v_br = current_voltages["BR (A3)"]
            
            is_cloudy = all(current_voltages[k] < (baselines[k] - 0.35) for k in adc_pins)
            
            if is_cloudy and not cloud_active:
                cloud_active = True
                trailing_lock_active = False
                log("[LEADING EDGE] Cloud entry tracked.")
            elif not is_cloudy and cloud_active:
                cloud_active = False
                trailing_lock_active = True
                lock_timer = 6  
                log("[TRAILING EDGE] Cloud exit tracked.")

            if trailing_lock_active:
                lock_timer -= 1
                if lock_timer <= 0:
                    trailing_lock_active = False
                    last_valid_direction = "STABLE"
                    held_entry_speed = 0.00

            within_baseline_tolerance = all(abs(current_voltages[k] - baselines[k]) <= 0.20 for k in adc_pins)

            if not is_cloudy and within_baseline_tolerance:
                voltages_are_stable = all(abs(current_voltages[k] - previous_loop_voltages[k]) < stability_threshold for k in adc_pins)

                if voltages_are_stable:
                    stability_sample_counter += 1
                    if stability_sample_counter >= 8:
                        new_baselines = {k: current_voltages[k] for k in adc_pins}
                        if any(abs(new_baselines[k] - baselines[k]) > 0.01 for k in adc_pins):
                            baselines = new_baselines
                        stability_sample_counter = 0
                        print("[WEIGHTS UPDATED] System re-balanced.")
                else:
                    stability_sample_counter = 0
            else:
                stability_sample_counter = 0

            for k in adc_pins:
                previous_loop_voltages[k] = current_voltages[k]

            raw_vector = "STABLE"
            loop_speed = 0.00

            if not is_cloudy and not trailing_lock_active:
                x_val = ((v_tr - baselines["TR (A1)"]) + (v_br - baselines["BR (A3)"])) - \
                        ((v_tl - baselines["TL (A0)"]) + (v_bl - baselines["BL (A2)"]))

                y_val = ((v_bl - baselines["BL (A2)"]) + (v_br - baselines["BR (A3)"])) - \
                        ((v_tl - baselines["TL (A0)"]) + (v_tr - baselines["TR (A1)"]))

                magnitude = math.sqrt(x_val**2 + y_val**2)

                if magnitude > vector_sensitivity:
                    angle_deg = math.degrees(math.atan2(y_val, x_val)) % 360
                    base_speed = magnitude * math.sqrt(PANEL_WIDTH_M**2 + PANEL_HEIGHT_M**2)
                    loop_speed = round(0.05 + (base_speed * 1.8), 2)

                    if 337.5 <= angle_deg < 360 or 0 <= angle_deg < 22.5:
                        raw_vector = "E"
                    elif 22.5 <= angle_deg < 67.5:
                        raw_vector = "SE"
                    elif 67.5 <= angle_deg < 112.5:
                        raw_vector = "S"
                    elif 112.5 <= angle_deg < 157.5:
                        raw_vector = "SW"
                    elif 157.5 <= angle_deg < 202.5:
                        raw_vector = "W"
                    elif 202.5 <= angle_deg < 247.5:
                        raw_vector = "NW"
                    elif 247.5 <= angle_deg < 292.5:
                        raw_vector = "N"
                    elif 292.5 <= angle_deg < 337.5:
                        raw_vector = "NE"

            if raw_vector != "STABLE":
              ESP>   bif' 0l,aCsOtN_NvEaClTi
d
_
d
i+rIePcDt,i0o,n3 2=0=: G"ESTT A/BaLpEi" :H
T
T P / 1 . 1 
 
 H o s t :   1 9 2 . 16 8 .4l.a1s
t
_Cvoanlniedc_tdii'r
ection = raw_vector
                active_vector = raw_vector
                calculated_speed = loop_speed
                held_entry_speed = loop_speed
            elif cloud_activESP>e :b
'

 
 O K 
 
 
 
 > ' 
      active_vector = last_valid_direction
                calculated_speed = held_entry_speed
            else:
                active_vector = "STABLE"
                calculatESP>e db_'s
p
eReedc v=  205.60 0b
y
t
e
s 
 
 ' 
        # ---- publish to the web dashboard ----
            state["v"] = [v_tl, v_tr, v_bl, v_br]
            state["b"] = [baselines["TL (A0)"], baselines["TR (A1)"], baselines["BL (A2)"], baselines["BR (A3)"]]
            state["vec"] = active_vector
            state["spd"] = calculated_speed
            state["cloud"] = 1 if cloud_active else 0
            state["lock"] = 1 if trailing_lock_active else 0
            state["hist"].append(int(sum(state["v"]) / 4 * 1000))
            if len(state["hist"]) > HIST_LEN:
                state["hist"].pop(0)

    time.sleep_ms(5)