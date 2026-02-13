from django.utils.text import slugify

from dcim.choices import DeviceStatusChoices
from dcim.models import Device, DeviceRole, DeviceType, Interface, Site
from ipam.choices import IPAddressStatusChoices
from ipam.models import IPAddress, Prefix

from extras.scripts import (
    Script,
    ObjectVar,
    StringVar,
    ChoiceVar,
)


class CreateDeviceAndAssignIP(Script):
    """
    Creates a new device, finds the next available IP from a chosen prefix,
    creates that IP address, and assigns it to a selected interface on the
    newly created device.

    Compatible with NetBox 4.4.x
    """

    class Meta:
        name = "Create Device & Assign Next Available IP"
        description = (
            "Create a new device, allocate the next available IP from a "
            "prefix, and assign it to an interface on the device."
        )
        field_order = [
            "device_name",
            "site",
            "device_role",
            "device_type",
            "device_status",
            "prefix",
            "interface",
            "ip_status",
        ]

    # ── Device fields ──────────────────────────────────────────────────
    device_name = StringVar(
        description="Name of the new device",
        label="Device Name",
    )

    site = ObjectVar(
        model=Site,
        description="Site where the device will be created",
        label="Site",
    )

    device_role = ObjectVar(
        model=DeviceRole,
        description="Role for the new device",
        label="Device Role",
    )

    device_type = ObjectVar(
        model=DeviceType,
        description="Hardware model / device type",
        label="Device Type",
    )

    device_status = ChoiceVar(
        choices=DeviceStatusChoices,
        description="Initial status for the device",
        label="Device Status",
        default=DeviceStatusChoices.STATUS_PLANNED,
    )

    # ── IP / Prefix fields ─────────────────────────────────────────────
    prefix = ObjectVar(
        model=Prefix,
        description="Select a prefix from which to allocate the next available IP",
        label="Prefix",
    )

    interface = ObjectVar(
        model=Interface,
        description=(
            "Interface on the new device to which the IP will be assigned. "
            "NOTE: Because the device does not exist yet at form-render time, "
            "this dropdown shows interfaces from the selected Device Type's "
            "template. After the device is created the script will locate the "
            "matching interface by name."
        ),
        label="Interface (template name)",
        required=False,
        # If you want to filter interfaces by device (useful when assigning
        # IPs to an *existing* device), you can use:
        #   query_params={"device_id": "$device"}
        # For new devices we rely on the interface template name (see run()).
    )

    ip_status = ChoiceVar(
        choices=IPAddressStatusChoices,
        description="Status to assign to the new IP address",
        label="IP Status",
        default=IPAddressStatusChoices.STATUS_ACTIVE,
    )

    # ── Execution ──────────────────────────────────────────────────────
    def run(self, data, commit):
        # ---- 1. Create the device ----
        device = Device(
            name=data["device_name"],
            site=data["site"],
            role=data["device_role"],
            device_type=data["device_type"],
            status=data["device_status"],
        )
        device.full_clean()
        device.save()
        self.log_success(f"Created device **{device}**")

        # ---- 2. Get the next available IP from the chosen prefix ----
        prefix = data["prefix"]
        available_ip = prefix.get_first_available_ip()

        if not available_ip:
            self.log_failure(
                f"No available IP addresses in prefix **{prefix}**"
            )
            return

        self.log_info(
            f"Next available IP in **{prefix}**: `{available_ip}`"
        )

        # ---- 3. Determine the target interface ----
        #
        # The user selected an Interface object from the dropdown.
        # If the interface belongs to a *different* device (or is a template
        # reference), we look up the matching interface by name on the
        # newly-created device.  NetBox auto-creates interfaces from the
        # device-type component templates when the device is saved, so a
        # matching interface should exist.
        target_iface = None
        selected_iface = data.get("interface")

        if selected_iface:
            # Try to find the interface on the new device by name
            target_iface = Interface.objects.filter(
                device=device, name=selected_iface.name
            ).first()

            if not target_iface:
                # Fall back: maybe the user picked an interface that already
                # belongs to this device (edge case on re-run, etc.)
                if (
                    selected_iface.device
                    and selected_iface.device.pk == device.pk
                ):
                    target_iface = selected_iface

            if not target_iface:
                self.log_warning(
                    f"Interface **{selected_iface.name}** was not found on "
                    f"device **{device}**. The IP will be created without an "
                    f"interface assignment."
                )

        # ---- 4. Create the IP address ----
        ip_address = IPAddress(
            address=available_ip,
            status=data["ip_status"],
        )

        # Assign to the interface if we found one
        if target_iface:
            ip_address.assigned_object = target_iface

        ip_address.full_clean()
        ip_address.save()

        if target_iface:
            self.log_success(
                f"Created IP **{ip_address}** and assigned to "
                f"interface **{target_iface}** on device **{device}**"
            )
        else:
            self.log_success(
                f"Created IP **{ip_address}** (no interface assignment)"
            )

        # ---- 5. Optionally set as primary IP for the device ----
        if target_iface:
            if ip_address.family == 4:
                device.primary_ip4 = ip_address
            else:
                device.primary_ip6 = ip_address
            device.full_clean()
            device.save()
            self.log_info(
                f"Set **{ip_address}** as the primary IPv{ip_address.family} "
                f"address for device **{device}**"
            )

        return f"Device '{device}' created with IP {ip_address}"