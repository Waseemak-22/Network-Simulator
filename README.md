# Network Simulator

## Overview

This project is a **Python-based Network Simulator** that demonstrates fundamental concepts of computer networking such as devices, network layers, and communication protocols.

The simulator models different networking components including **hubs, bridges, switches, and end devices**, along with implementations of common **data link layer protocols** like Stop-and-Wait and Sliding Window.

The goal of this project is to help understand how data flows through different network layers and devices.

---

## Project Structure

```
Network_Simulator
│
├── devices
│   ├── bridge.py
│   ├── end_device.py
│   ├── hub.py
│   └── switch.py
│
├── layers
│   ├── physical_layer.py
│   └── data_link_layer.py
│
├── protocols
│   ├── crc.py
│   ├── csma_cd.py
│   ├── sliding_window.py
│   └── stop_and_wait.py
│
├── topology
│   └── topology_manager.py
│
├── utils
│
└── main.py
```

---

## Components

### Devices

Implements basic networking devices used in local area networks.

* **Hub** – Broadcasts frames to all connected devices.
* **Bridge** – Connects multiple network segments and filters traffic.
* **Switch** – Uses MAC address table to forward frames efficiently.
* **End Device** – Represents hosts that send and receive data.

---

### Layers

#### Physical Layer

Handles the physical transmission of bits across the communication channel.

#### Data Link Layer

Responsible for:

* Frame creation
* Error detection
* Medium access control

---

### Protocols

The project includes implementations of common data link layer protocols:

* **CRC (Cyclic Redundancy Check)** – Error detection mechanism
* **CSMA/CD** – Carrier Sense Multiple Access with Collision Detection
* **Stop and Wait Protocol** – Simple flow control mechanism
* **Sliding Window Protocol** – Efficient data transmission with multiple frames

---

### Topology Manager

Handles network structure and manages connections between devices.

---

## Requirements

* Python 3.x

Install Python dependencies (if needed):

```
pip install -r requirements.txt
```

---

## How to Run

Run the main simulation file:

```
python main.py
```

This will start the network simulation and demonstrate communication between devices using the implemented protocols.

---

## Learning Objectives

This project helps in understanding:

* Computer Network architecture
* Data Link Layer protocols
* Error detection techniques
* Flow control mechanisms
* Network device behavior

---

## Future Improvements

Possible enhancements include:

* GUI visualization of network topology
* Support for additional routing protocols
* Packet-level simulation
* Performance analysis tools

---

## Author

Developed as part of a **Computer Networks / Networking Simulation project**.
