from dcim.models import Device, Interface
from ipam.models import Prefix, IPAddress
from extras.scripts import Script, ObjectVar, StringVar
from django.core.exceptions import ObjectDoesNotExist


class AssignIPToInterface(Script):
    class Meta:
        name = "Assign IP to Device Interface"
        description = "Select a device and prefix, then assign the next available IP to a specified interface"
        commit_default = True

    device = ObjectVar(
        model=Device,
        query_params={
            'status': 'active',
        },
        description="Select the device",
        required=True
    )

    prefix = ObjectVar(
        model=Prefix,
        query_params={
            'status': 'active',
        },
        description="Select the prefix to get next available IP from",
        required=True
    )

    interface_name = StringVar(
        description="Enter the interface name (e.g., eth0, GigabitEthernet0/0/1)",
        required=True
    )

    def run(self, data, commit):
        device = data['device']
        prefix = data['prefix']
        interface_name = data['interface_name']

        # Find the interface on the device
        try:
            selected_interface = Interface.objects.get(
                device=device,
                name=interface_name
            )
        except ObjectDoesNotExist:
            self.log_failure(f"Interface '{interface_name}' not found on device {device.name}")
            self.log_info(f"Available interfaces on {device.name}:")
            for iface in Interface.objects.filter(device=device, enabled=True):
                self.log_info(f"  - {iface.name} ({iface.type})")
            return

        if not selected_interface.enabled:
            self.log_warning(f"Interface {interface_name} is disabled")

        # Check if interface already has an IP
        existing_ips = IPAddress.objects.filter(assigned_object_id=selected_interface.id)
        if existing_ips.exists():
            self.log_warning(f"Interface already has IP addresses:")
            for ip in existing_ips:
                self.log_warning(f"  - {ip.address}")

        # Get the next available IP from the prefix
        next_ip = prefix.get_first_available_ip()

        if not next_ip:
            self.log_failure(f"No available IPs in prefix {prefix.prefix}")
            return

        # Create the IP address and assign it to the interface
        ip_address = IPAddress(
            address=f"{next_ip}/{prefix.prefix.prefixlen}",
            vrf=prefix.vrf,
            tenant=device.tenant,
            status='active',
            assigned_object=selected_interface,
            description=f"Auto-assigned to {device.name} - {selected_interface.name}"
        )

        if commit:
            ip_address.save()
            self.log_success(
                f"Successfully assigned {ip_address.address} to "
                f"{device.name} - {selected_interface.name}"
            )
        else:
            self.log_info(
                f"[DRY RUN] Would assign {ip_address.address} to "
                f"{device.name} - {selected_interface.name}"
            )

        return f"IP {ip_address.address} assigned to interface {selected_interface.name}"