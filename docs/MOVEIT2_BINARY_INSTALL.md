# MoveIt 2 — Binary Install (ROS 2 Jazzy)

This guide documents how to install MoveIt 2 from binary packages on **Ubuntu 24.04** with **ROS 2 Jazzy**, as described on the official MoveIt site.

**Source:** [MoveIt 2 Binary Install](https://moveit.ai/install-moveit2/binary/)

---

## Prerequisites

Install ROS 2 Jazzy first: [ROS 2 Jazzy Ubuntu Installation](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debians.html).

---

## Install MoveIt 2

```bash
sudo apt install ros-jazzy-moveit
```

---

## Middleware (recommended)

MoveIt recommends **CycloneDDS** as the DDS middleware.

> **Note:** Using CycloneDDS makes all nodes started with this RMW incompatible with nodes using a different DDS (e.g. default Fast DDS).

1. Install the CycloneDDS RMW package:

   ```bash
   sudo apt install ros-jazzy-rmw-cyclonedds-cpp
   ```

2. Set the RMW implementation for your shell:

   ```bash
   export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
   ```

3. (Optional) Add the export to `~/.bashrc` so it is set automatically:

   ```bash
   echo 'export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp' >> ~/.bashrc
   ```

---

## Quick start

After installing, you can start planning in RViz using the [MoveIt 2 Getting Started Tutorial](https://moveit.picknik.ai/main/doc/tutorials/getting_started/getting_started.html).

---

## Other setups

- **Source build (Linux):** See [MoveIt 2 build instructions](https://moveit.picknik.ai/main/doc/contributing/code.html).
- **Virtual machines:** Prefer a native Ubuntu install. If you use a VM, VMware is recommended; there are known issues with RViz when using VirtualBox (enable virtualization in BIOS if needed).
