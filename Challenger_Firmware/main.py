from machine import Pin, ADC, I2C
import time
import ssd1306
import framebuf

# ==========================================
# 1. HARDWARE CONFIGURATION & INITIALIZATION
# ==========================================
# Target hardware analog pins mapping directly to the Challenger A0-A3 layout
adc_pins = {
    "TL (A0)": ADC(Pin(26)), # Top-Left
    "TR (A1)": ADC(Pin(27)), # Top-Right
    "BL (A2)": ADC(Pin(28)), # Bottom-Left
    "BR (A3)": ADC(Pin(29))  # Bottom-Right
}

# 1:1 hardware divider scaling factor (two 5.6k resistors = 2.0x multiplier)
conversion_factor = 6.6 / 65535

# Initialize DFR0647 OLED Display (128x32 I2C on Pins GP0 & GP1)
i2c = I2C(0, sda=Pin(0), scl=Pin(1), freq=400000)
oled = ssd1306.SSD1306_I2C(128, 32, i2c)

# ==========================================
# 2. 16x16 DIRECTIONAL VECTOR SPRITE GRAPHICS
# ==========================================
# Hand-crafted binary bitmaps (32 bytes each) for 16x16 Mono HLSB rendering
arrow_n  = bytearray([0x01, 0x80, 0x03, 0xC0, 0x07, 0xE0, 0x0F, 0xF0, 0x1B, 0xD8, 0x33, 0xCC, 0x03, 0xC0, 0x03, 0xC0, 0x03, 0xC0, 0x03, 0xC0, 0x03, 0xC0, 0x03, 0xC0, 0x03, 0xC0, 0x03, 0xC0, 0x03, 0xC0, 0x00, 0x00])
arrow_s  = bytearray([0x00, 0x00, 0x03, 0xC0, 0x03, 0xC0, 0x03, 0xC0, 0x03, 0xC0, 0x03, 0xC0, 0x03, 0xC0, 0x03, 0xC0, 0x03, 0xC0, 0x03, 0xC0, 0x33, 0xCC, 0x1B, 0xD8, 0x0F, 0xF0, 0x07, 0xE0, 0x03, 0xC0, 0x01, 0x80])
arrow_e  = bytearray([0x00, 0x00, 0x00, 0x08, 0x00, 0x1C, 0x00, 0x3E, 0x00, 0x7F, 0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x7F, 0x00, 0x7F, 0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x7F, 0x00, 0x3E, 0x00, 0x1C, 0x00, 0x08, 0x00, 0x00])
arrow_w  = bytearray([0x00, 0x00, 0x20, 0x00, 0x70, 0x00, 0xF8, 0x00, 0xFE, 0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0xFE, 0x00, 0xFE, 0x00, 0xFF, 0xFF, 0xFF, 0xFF, 0xFE, 0x00, 0xF8, 0x00, 0x70, 0x00, 0x20, 0x00, 0x00, 0x00])

arrow_ne = bytearray([0x03, 0xFF, 0x01, 0xFF, 0x00, 0x7F, 0x00, 0x3F, 0x00, 0x7B, 0x00, 0xF1, 0x01, 0xE0, 0x03, 0xC0, 0x07, 0x80, 0x0F, 0x00, 0x1E, 0x00, 0x3C, 0x00, 0x78, 0x00, 0xF0, 0x00, 0xE0, 0x00, 0x00, 0x00])
arrow_nw = bytearray([0xFF, 0xC0, 0xFF, 0x80, 0xFE, 0x00, 0xFC, 0x00, 0xDE, 0x00, 0x8F, 0x00, 0x07, 0x80, 0x03, 0xC0, 0x01, 0xE0, 0x00, 0xF0, 0x00, 0x78, 0x00, 0x3C, 0x00, 0x1E, 0x00, 0x0F, 0x00, 0x07, 0x00, 0x00])
arrow_se = bytearray([0x00, 0x00, 0xE0, 0x00, 0xF0, 0x00, 0x78, 0x00, 0x3C, 0x00, 0x1E, 0x00, 0x0F, 0x00, 0x07, 0x80, 0x03, 0xC0, 0x01, 0xE0, 0x00, 0xF1, 0x00, 0x7B, 0x00, 0x3F, 0x00, 0x7F, 0x01, 0xFF, 0x03, 0xFF])
arrow_sw = bytearray([0x00, 0x00, 0x07, 0x00, 0x0F, 0x00, 0x1E, 0x00, 0x3C, 0x00, 0x78, 0x00, 0xF0, 0x00, 0x07, 0x80, 0x03, 0xC0, 0x01, 0xE0, 0x8F, 0x00, 0xDE, 0x00, 0xFC, 0x00, 0xFE, 0x00, 0xFF, 0x80, 0xFF, 0xC0])

stable_i = bytearray([0x00, 0x00, 0x3F, 0xFC, 0x3F, 0xFC, 0x30, 0x0C, 0x30, 0x0C, 0x30, 0x0C, 0x30, 0x0C, 0x30, 0x0C, 0x30, 0x0C, 0x30, 0x0C, 0x30, 0x0C, 0x30, 0x0C, 0x3F, 0xFC, 0x3F, 0xFC, 0x00, 0x00, 0x00, 0x00])

def make_buffer(b_arr):
    return framebuf.FrameBuffer(b_arr, 16, 16, framebuf.MONO_HLSB)

sprites = {
    "EAST": make_buffer(arrow_e), "WEST": make_buffer(arrow_w), 
    "NORTH": make_buffer(arrow_n), "SOUTH": make_buffer(arrow_s),
    "NE": make_buffer(arrow_ne), "NW": make_buffer(arrow_nw), 
    "SE": make_buffer(arrow_se), "SW": make_buffer(arrow_sw),
    "STABLE": make_buffer(stable_i)
}

# ==========================================
# 3. TRACKING PARAMETERS & BUFFERS
# ==========================================
last_voltages = {label: 0.0 for label in adc_pins}
stability_threshold = 0.03
vector_sensitivity = 0.15  # 150mV cross-axis threshold for a valid moving shadow edge

# Rolling graph memory data pipeline (Width: 58 pixels allocated on the right half)
graph_history = []
max_graph_points = 58

oled.fill(0)
oled.text("AEOLUS-NET READY", 2, 12)
oled.show()
time.sleep(1.0)

# ==========================================
# 4. MASTER EXECUTION LOOP
# ==========================================
while True:
    output_strings = []
    
    for label, adc_channel in adc_pins.items():
        # 1. Smooth out crosstalk noise by oversampling 16 times
        total = 0
        for _ in range(16):
            total += adc_channel.read_u16()
            
        raw_average = total / 16
        measured_voltage = raw_average * conversion_factor
        
        if measured_voltage < 0.05:
            measured_voltage = 0.0
            
        # 3. Stability filter: Only accept changes greater than or equal to 0.03V
        if abs(measured_voltage - last_voltages[label]) >= stability_threshold:
            last_voltages[label] = measured_voltage
        
        output_strings.append(f"{label}: {last_voltages[label]:.2f}V")

    # Console telemetry print out 
    print(" | ".join(output_strings))
    
    # Extract clean stabilized variables for vector analytics
    v_tl = last_voltages["TL (A0)"]
    v_tr = last_voltages["TR (A1)"]
    v_bl = last_voltages["BL (A2)"]
    v_br = last_voltages["BR (A3)"]
    
    # 5. 8-WAY SPATIAL VECTOR MATHEMATICS
    # Subtraction cancels out uniform room illumination noise
    delta_X = v_tr - v_tl  # Positive = Shadow hits Left side first
    delta_Y = v_bl - v_tl  # Positive = Shadow hits Top side first
    
    comp_x = ""
    comp_y = ""
    calculated_speed = 0.00
    
    if abs(delta_X) > vector_sensitivity:
        comp_x = "EAST" if delta_X > 0 else "WEST"
    if abs(delta_Y) > vector_sensitivity:
        comp_y = "SOUTH" if delta_Y > 0 else "NORTH"
        
    # Derive absolute composite direction vector and simulate realistic speed
    if comp_x and comp_y:
        active_vector = f"{comp_y}{comp_x}"  # Combines into NW, NE, SW, SE
        calculated_speed = round(0.18 + (max(abs(delta_X), abs(delta_Y)) * 0.5), 2)
    elif comp_x:
        active_vector = comp_x
        calculated_speed = round(0.12 + (abs(delta_X) * 0.4), 2)
    elif comp_y:
        active_vector = comp_y
        calculated_speed = round(0.12 + (abs(delta_Y) * 0.4), 2)
    else:
        active_vector = "STABLE"

    # Add the overall system voltage average to your scrolling chart buffer
    system_avg_voltage = (v_tl + v_tr + v_bl + v_br) / 4
    graph_history.append(system_avg_voltage)
    if len(graph_history) > max_graph_points:
        graph_history.pop(0)

    # ==========================================
    # 6. OLED PIXEL RENDERING ENGINE (128x32)
    # ==========================================
    oled.fill(0) # Flush pixels
    
    # Section A: Draw Vector Sprite (Left side: 16x16 centered vertically at y=8)
    oled.blit(sprites[active_vector], 0, 8)
    
    # Section B: Print Speed Telemetry (Center area)
    oled.text(f"{calculated_speed:.2f}", 18, 4)
    oled.text("m/s", 18, 18)
    
    # Section C: Prototyping Interface Partition Border
    oled.vline(66, 0, 32, 1)
    
    # Section D: Generate Rolling Voltage Sparkline Chart
    # Plot bounds: Width X=68 to X=126, Height Y=2 to Y=30
    for idx, sample_voltage in enumerate(graph_history):
        x_pixel = 68 + idx
        # Map 0V-5V linearly to the 32-pixel layout height:
        # 5V will draw near y=2 (top), 0V will draw near y=30 (bottom)
        y_pixel = int(30 - (sample_voltage * 5.6))
        y_safe = max(2, min(y_pixel, 30))
        oled.pixel(x_pixel, y_safe, 1)

    oled.show() # Push to hardware pixels
    
    time.sleep(0.1) # Accelerated 10Hz loops for sharp tracking response
