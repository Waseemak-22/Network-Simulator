# 🌐 Final NetSim v2

Final NetSim v2 is a modular **Computer Network Simulator** built using **Python** and **Flask** to demonstrate networking concepts from the **Physical Layer** and **Data Link Layer** of the OSI Model.

The project simulates communication between network devices such as hubs, switches, and bridges while implementing flow control, access control, and error control mechanisms.

---

# 🚀 Features

- Physical Layer simulation
  - End devices
  - Hubs
  - Network topology management

- Data Link Layer simulation
  - Frame transmission
  - Switch communication
  - Bridge forwarding
  - CSMA/CD access control
  - Sliding Window flow control
  - Error control mechanisms

- Flask-based backend APIs
- Interactive web interface
- Modular and scalable architecture

---

# 🛠 Technologies Used

- Python 3
- Flask
- HTML
- CSS
- JavaScript

---

# 📂 Project Structure

```text
final_netsim/
│
├── app.py
├── requirements.txt
│
├── physical_layer/
│   ├── device.py
│   ├── hub.py
│   └── topology.py
│
├── datalink_layer/
│   ├── frame.py
│   ├── switch.py
│   ├── bridge.py
│   ├── access_control.py
│   ├── flow_control.py
│   └── error_control.py
│
├── templates/
│   └── index.html
│
└── utils/
    └── logger.py
