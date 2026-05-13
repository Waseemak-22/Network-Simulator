from flask import Flask, render_template, request, jsonify
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from physical_layer.device    import EndDevice
from physical_layer.hub       import Hub
from physical_layer.topology  import Topology, MULTICAST_MAC
from datalink_layer.frame     import Frame
from datalink_layer.switch    import Switch
from datalink_layer.bridge    import Bridge
from datalink_layer.error_control  import ErrorControl
from datalink_layer.access_control import CSMACD, Channel
from datalink_layer.flow_control   import SlidingWindow
from utils.logger import logger

app = Flask(__name__)
sim = {}

def reset_sim():
    logger.clear()
    sim['topo']    = Topology('Network')
    sim['channel'] = Channel()

reset_sim()

def T(): return sim['topo']
def ok(**kw): return jsonify({'status': 'ok', **kw})

# ── pages ──────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

# ── core ───────────────────────────────────────────────────────
@app.route('/api/reset', methods=['POST'])
def api_reset():
    reset_sim()
    return ok(message='Reset done')

@app.route('/api/topology')
def api_topo():
    return jsonify(T().summary())

@app.route('/api/logs')
def api_logs():
    return jsonify({'logs': logger.recent(300)})

# ── build ──────────────────────────────────────────────────────
@app.route('/api/add_device', methods=['POST'])
def api_add_device():
    d = request.json
    name  = d.get('name', '').strip()
    group = d.get('multicast_group') or None
    t = T()
    if not name:          return jsonify({'error': 'Name required'})
    if name in t.devices: return jsonify({'error': f'{name} already exists'})
    dev = t.add_device(name, multicast_group=group)
    return ok(device=dev.to_dict(), topology=t.summary())

@app.route('/api/add_hub', methods=['POST'])
def api_add_hub():
    d = request.json
    name, ports = d.get('name', '').strip(), int(d.get('ports', 8))
    t = T()
    if not name:       return jsonify({'error': 'Name required'})
    if name in t.hubs: return jsonify({'error': f'{name} already exists'})
    h = t.add_hub(name, ports)
    return ok(hub=h.to_dict(), topology=t.summary())

@app.route('/api/add_switch', methods=['POST'])
def api_add_switch():
    d = request.json
    name, ports = d.get('name', '').strip(), int(d.get('ports', 8))
    t = T()
    if not name:           return jsonify({'error': 'Name required'})
    if name in t.switches: return jsonify({'error': f'{name} already exists'})
    s = t.add_switch(name, ports)
    return ok(switch=s.to_dict(), topology=t.summary())

@app.route('/api/add_bridge', methods=['POST'])
def api_add_bridge():
    d = request.json
    name = d.get('name', '').strip()
    t = T()
    if not name:           return jsonify({'error': 'Name required'})
    if name in t.bridges:  return jsonify({'error': f'{name} already exists'})
    b = t.add_bridge(name)
    return ok(bridge=b.to_dict(), topology=t.summary())

@app.route('/api/connect', methods=['POST'])
def api_connect():
    d = request.json
    src, dst, ctype = d.get('src'), d.get('dst'), d.get('type')
    t = T()
    try:
        if   ctype == 'device_hub':    t.connect_to_hub(src, dst)
        elif ctype == 'device_switch': t.connect_to_switch(src, dst)
        elif ctype == 'hub_switch':    t.connect_hub_to_switch(src, dst)
        elif ctype == 'hub_bridge':    t.connect_hub_to_bridge(src, dst)
        elif ctype == 'device_bridge': t.connect_device_to_bridge(src, dst)
        else: return jsonify({'error': f'Unknown type: {ctype}'})
        return ok(topology=t.summary())
    except Exception as e:
        return jsonify({'error': str(e)})

# ── transmit ───────────────────────────────────────────────────
@app.route('/api/send', methods=['POST'])
def api_send():
    d      = request.json
    src_n  = d.get('src')
    dst_n  = d.get('dst')
    msg    = d.get('message', 'Hello')
    stype  = d.get('send_type', 'unicast')
    t      = T()

    if src_n not in t.devices:
        return jsonify({'error': f'Device {src_n} not found'})

    src = t.devices[src_n]
    logger.log('INFO', f'══════ {stype.upper()}: "{msg}" from {src_n} ══════', {})

    if stype == 'broadcast':
        frame = src.send_broadcast(msg)
    elif stype == 'multicast':
        frame = src.send_multicast(msg, MULTICAST_MAC)
    else:
        if dst_n not in t.devices:
            return jsonify({'error': f'Device {dst_n} not found'})
        frame = src.send_unicast(msg, t.devices[dst_n].mac)

    receivers = [dev.name for dev in t.devices.values()
                 if any(e.get('frame_id') == frame.frame_id for e in dev.inbox)]
    if receivers:
        logger.log('SUMMARY', f'✅ Delivered to: {", ".join(receivers)}',
                   {'receivers': receivers})
    else:
        logger.log('SUMMARY', '⚠️  No device received the frame', {})

    return ok(frame=frame.to_dict(), receivers=receivers,
              logs=logger.recent(300), topology=t.summary())

# ── test scenarios ─────────────────────────────────────────────
@app.route('/api/test/p2p', methods=['POST'])
def test_p2p():
    reset_sim(); t = T()
    pc1 = t.add_device('PC1')
    pc2 = t.add_device('PC2')
    # direct connection — no hub, no switch
    pc1.connected_to   = pc2
    pc1.port_on_device = 1
    pc2.connected_to   = pc1
    pc2.port_on_device = 1
    logger.log('TEST', '══════ TEST 0: POINT-TO-POINT (Direct PC to PC) ══════', {})
    logger.log('INFO', 'PC1 and PC2 are connected DIRECTLY — no hub, no switch.', {})
    logger.log('INFO', 'This is the simplest network: just a cable between two computers.', {})
    logger.log('INFO', 'PC1 sends UNICAST "Hello PC2!" directly to PC2.', {})
    frame = pc1.send_unicast('Hello PC2!', pc2.mac)
    logger.log('INFO', f'Frame ID: {frame.frame_id}  |  CRC: {frame.crc}  |  Valid: {frame.valid()}', {})
    received = pc2.recv_count > 0
    if received:
        logger.log('SUMMARY', f'✅ PC2 received the frame directly — no broadcasting needed!', {'frame_id': frame.frame_id})
    else:
        logger.log('SUMMARY', '❌ Delivery failed', {})
    logger.log('INFO', 'Collision Domains: 1  |  Broadcast Domains: 1', {})
    return ok(logs=logger.recent(300), topology=t.summary())


@app.route('/api/test/unicast', methods=['POST'])
def test_unicast():
    reset_sim(); t = T()
    t.add_hub('HUB1')
    for i in range(1, 6):
        t.add_device(f'PC{i}')
        t.connect_to_hub(f'PC{i}', 'HUB1')
    logger.log('TEST', '══════ TEST 1: UNICAST via HUB ══════', {})
    logger.log('INFO', 'PC1 sends UNICAST to PC3 only.', {})
    logger.log('INFO', 'Hub broadcasts to ALL ports — but only PC3 MAC matches → accepts.', {})
    logger.log('INFO', 'PC2, PC4, PC5 receive frame but discard it (not their MAC).', {})
    t.devices['PC1'].send_unicast('Hello PC3!', t.devices['PC3'].mac)
    recvrs = [d.name for d in t.devices.values() if d.recv_count > 0]
    discards = [d.name for d in t.devices.values() if d.recv_count == 0 and d.name != 'PC1']
    logger.log('SUMMARY', f'✅ Accepted by: {recvrs}  |  🗑 Discarded by: {discards}', {})
    return ok(logs=logger.recent(300), topology=t.summary())

@app.route('/api/test/broadcast', methods=['POST'])
def test_broadcast():
    reset_sim(); t = T()
    t.add_hub('HUB1')
    for i in range(1, 6):
        t.add_device(f'PC{i}')
        t.connect_to_hub(f'PC{i}', 'HUB1')
    logger.log('TEST', '══════ TEST 2: BROADCAST via HUB ══════', {})
    logger.log('INFO', 'PC1 sends to FF:FF:FF:FF:FF:FF (broadcast address).', {})
    logger.log('INFO', 'Hub broadcasts to all ports. ALL devices accept it — no discards.', {})
    t.devices['PC1'].send_broadcast('Hello EVERYONE!')
    recvrs = [d.name for d in t.devices.values() if d.recv_count > 0]
    logger.log('SUMMARY', f'✅ Broadcast received by ALL: {recvrs}', {})
    return ok(logs=logger.recent(300), topology=t.summary())

@app.route('/api/test/multicast', methods=['POST'])
def test_multicast():
    reset_sim(); t = T()
    t.add_hub('HUB1')
    t.add_device('PC1')
    t.add_device('PC2', multicast_group='VideoGroup')
    t.add_device('PC3')
    t.add_device('PC4', multicast_group='VideoGroup')
    t.add_device('PC5')
    for i in range(1, 6):
        t.connect_to_hub(f'PC{i}', 'HUB1')
    logger.log('TEST', '══════ TEST 3: MULTICAST via HUB ══════', {})
    logger.log('INFO', 'PC1 sends MULTICAST to group 01:00:5E:00:00:01.', {})
    logger.log('INFO', 'PC2 and PC4 are in VideoGroup → they ACCEPT.', {})
    logger.log('INFO', 'PC3 and PC5 have no group → they DISCARD.', {})
    t.devices['PC1'].send_multicast('Video Stream Data!', MULTICAST_MAC)
    recvrs = [d.name for d in t.devices.values() if d.recv_count > 0]
    discards = [d.name for d in t.devices.values() if d.recv_count == 0 and d.name != 'PC1']
    logger.log('SUMMARY', f'✅ Group members received: {recvrs}  |  🗑 Non-members discarded: {discards}', {})
    return ok(logs=logger.recent(300), topology=t.summary())

@app.route('/api/test/switch_mac', methods=['POST'])
def test_switch():
    reset_sim(); t = T()
    t.add_switch('SW1')
    for i in range(1, 6):
        t.add_device(f'PC{i}')
        t.connect_to_switch(f'PC{i}', 'SW1')
    logger.log('TEST', '══════ TEST 4: SWITCH + MAC LEARNING ══════', {})
    logger.log('INFO', 'Round 1 — PC1→PC3: Switch FLOODS (MAC unknown). Learns PC1 MAC.', {})
    t.devices['PC1'].send_unicast('Hi PC3 (round 1)', t.devices['PC3'].mac)
    logger.log('INFO', 'Round 2 — PC2→PC4: Switch FLOODS again. Learns PC2, PC3 MACs.', {})
    t.devices['PC2'].send_unicast('Hi PC4', t.devices['PC4'].mac)
    logger.log('INFO', 'Round 3 — PC1→PC3 AGAIN: Switch now FORWARDS directly! No flood.', {})
    t.devices['PC1'].send_unicast('Hi PC3 (round 2 — direct!)', t.devices['PC3'].mac)
    return ok(logs=logger.recent(300), topology=t.summary())

@app.route('/api/test/dual_star', methods=['POST'])
def test_dual():
    reset_sim(); t = T()
    t.add_hub('HUB1')
    t.add_hub('HUB2')
    t.add_switch('SW1')
    for i in range(1, 6):
        t.add_device(f'PC{i}')
        t.connect_to_hub(f'PC{i}', 'HUB1')
    for i in range(6, 11):
        t.add_device(f'PC{i}')
        t.connect_to_hub(f'PC{i}', 'HUB2')
    t.connect_hub_to_switch('HUB1', 'SW1', port=1)
    t.connect_hub_to_switch('HUB2', 'SW1', port=2)
    s = t.summary()
    logger.log('TEST', '══════ TEST 5: DUAL STAR via SWITCH ══════', {})
    logger.log('INFO', '10 PCs | HUB1 (PC1–5) ──SW1── HUB2 (PC6–10)', {})
    logger.log('INFO', f'Collision Domains: {s["total_collision_domains"]}  |  Broadcast Domains: {s["total_broadcast_domains"]}', {})
    logger.log('INFO', 'PC1 (on HUB1) sends UNICAST to PC8 (on HUB2) — cross network!', {})
    t.devices['PC1'].send_unicast('Cross-network Hello to PC8!', t.devices['PC8'].mac)
    recvrs = [d.name for d in t.devices.values() if d.recv_count > 0]
    logger.log('SUMMARY', f'✅ Received by: {recvrs}', {})
    return ok(logs=logger.recent(300), topology=t.summary())

@app.route('/api/test/bridge', methods=['POST'])
def test_bridge():
    reset_sim(); t = T()
    t.add_hub('HUB1')
    t.add_hub('HUB2')
    t.add_bridge('BR1')
    t.add_device('PC1'); t.add_device('PC2')
    t.connect_to_hub('PC1', 'HUB1')
    t.connect_to_hub('PC2', 'HUB1')
    t.add_device('PC3'); t.add_device('PC4')
    t.connect_to_hub('PC3', 'HUB2')
    t.connect_to_hub('PC4', 'HUB2')
    t.connect_hub_to_bridge('HUB1', 'BR1')
    t.connect_hub_to_bridge('HUB2', 'BR1')
    logger.log('TEST', '══════ TEST 6: BRIDGE ══════', {})
    logger.log('INFO', '[PC1, PC2] ── HUB1 ── BR1 ── HUB2 ── [PC3, PC4]', {})
    logger.log('INFO', 'Bridge connects 2 separate hub segments.', {})
    logger.log('INFO', 'Step 1: PC1 → PC2 (SAME segment). Bridge FILTERS — no crossing.', {})
    t.devices['PC1'].send_unicast('Hello PC2 (same side)', t.devices['PC2'].mac)
    logger.log('INFO', 'Step 2: PC1 → PC3 (DIFFERENT segment). Bridge FORWARDS across.', {})
    t.devices['PC1'].send_unicast('Hello PC3 (other side!)', t.devices['PC3'].mac)
    logger.log('INFO', 'Step 3: PC1 BROADCAST — Bridge FLOODS to both segments.', {})
    t.devices['PC1'].send_broadcast('Broadcast to ALL!')
    recvrs = list({d.name for d in t.devices.values() if d.recv_count > 0})
    logger.log('SUMMARY', f'✅ Total devices that received at least 1 frame: {recvrs}', {})
    return ok(logs=logger.recent(300), topology=t.summary())

@app.route('/api/test/error_control', methods=['POST'])
def test_error():
    reset_sim(); t = T()
    pc1 = t.add_device('PC1')
    pc2 = t.add_device('PC2')
    logger.log('TEST', '══════ TEST 7: ERROR CONTROL (CRC) ══════', {})
    f = Frame(pc1.mac, pc2.mac, 'NetworkData')
    logger.log('INFO', f'Frame created  data="NetworkData"  CRC={f.crc}', {})
    logger.log('INFO', 'Step 1: Check VALID frame — CRC should match.', {})
    r1 = ErrorControl.check(f)
    logger.log('INFO', 'Step 2: Corrupt the frame and re-check — CRC should MISMATCH.', {})
    r2 = ErrorControl.corrupt_and_check(f)
    logger.log('INFO', 'Step 3: Parity check on original data.', {})
    p = ErrorControl.parity('NetworkData')
    return ok(valid=r1, corrupt=r2, parity=p,
              logs=logger.recent(300), topology=t.summary())

@app.route('/api/test/csmacd', methods=['POST'])
def test_csma():
    reset_sim(); t = T()
    pc1 = t.add_device('PC1')
    pc2 = t.add_device('PC2')
    t.add_hub('HUB1')
    t.connect_to_hub('PC1', 'HUB1')
    t.connect_to_hub('PC2', 'HUB1')
    logger.log('TEST', '══════ TEST 8: CSMA/CD ACCESS CONTROL ══════', {})
    logger.log('INFO', 'PC1 and PC2 both try to use the SAME shared channel (hub).', {})
    logger.log('INFO', 'CSMA/CD: Sense → Transmit → Detect Collision → Backoff → Retry.', {})
    ch = sim['channel']
    csma = CSMACD(ch)
    f1 = Frame(pc1.mac, pc2.mac, 'Frame from PC1')
    f2 = Frame(pc2.mac, pc1.mac, 'Frame from PC2')
    r1 = csma.transmit('PC1', f1)
    r2 = csma.transmit('PC2', f2)
    logger.log('SUMMARY',
        f'PC1: {"✅ success" if r1["success"] else "❌ failed"}  |  PC2: {"✅ success" if r2["success"] else "❌ failed"}  |  Total collisions: {ch.collisions}', {})
    return ok(pc1=r1, pc2=r2,
              channel={'collisions': ch.collisions, 'successes': ch.successes},
              logs=logger.recent(300), topology=t.summary())

@app.route('/api/test/flow_control', methods=['POST'])
def test_flow():
    d      = request.json or {}
    mode   = d.get('mode', 'GBN')
    window = int(d.get('window_size', 4))
    reset_sim(); t = T()
    t.add_device('PC1')
    t.add_device('PC2')
    chunks = ['Hello', 'World', 'From', 'PC1', 'To', 'PC2', 'Via', 'Sliding']
    logger.log('TEST', f'══════ TEST 9: FLOW CONTROL ({mode}) | Window={window} ══════', {})
    sw = SlidingWindow(window_size=window, mode=mode, error_rate=0.25)
    result = sw.transmit('PC1', 'PC2', chunks)
    return ok(result=result, logs=logger.recent(300), topology=t.summary())

if __name__ == '__main__':
    print('\n  ╔══════════════════════════════════╗')
    print('  ║   NetSim — Network Simulator      ║')
    print('  ║   Open: http://localhost:5000      ║')
    print('  ╚══════════════════════════════════╝\n')
    app.run(debug=True, port=5000)
