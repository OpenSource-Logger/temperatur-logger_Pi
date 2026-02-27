export type Device = {
    chip_id: string;
    ip_last: string | null;
    device_id: string | null;
    sensor_type: string | null;
    sensor_params: string | null;
    created_at: number;
    last_seen: number;
};