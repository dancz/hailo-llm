
import hailo_platform.pyhailort._pyhailort as _pyhailort

print("Attributes of VDeviceParams:")
print(dir(_pyhailort.VDeviceParams))

try:
    params = _pyhailort.VDeviceParams.default()
    print("\nDefault params attributes:")
    print(dir(params))
    
    print("\nparams.multi_process_service (if exists):")
    if hasattr(params, 'multi_process_service'):
        print(params.multi_process_service)
    else:
        print("multi_process_service not found")
        
    print("\nparams.group_id (if exists):")
    if hasattr(params, 'group_id'):
        print(params.group_id)
    else:
        print("group_id not found")

    print("\nparams.device_count (if exists):")
    if hasattr(params, 'device_count'):
        print(params.device_count)
    else:
        print("device_count not found")

except Exception as e:
    print(f"Error: {e}")
