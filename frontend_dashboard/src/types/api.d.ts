// API Types and Interfaces

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
}

export interface ApiError {
  detail: string | object;
  error_code?: string;
}

// User & Auth Types
export interface User {
  id: number;
  username: string;
  full_name?: string;
  role: 'admin' | 'operator' | 'viewer';
  is_active: boolean;
  created_at: string;
}

export interface LoginParams {
  username: string;
  password: string;
}

export interface CreateUserParams {
  username: string;
  full_name?: string;
  password: string;
  role: 'admin' | 'operator' | 'viewer';
}

export interface UpdateUserParams extends Partial<CreateUserParams> {
  is_active?: boolean;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

// Device Types
export type DeviceStatus = 'online' | 'offline' | 'maintenance';

/** 设备视频流状态（从设备列表接口返回） */
export interface DeviceStreamStatus {
  is_active: boolean;
  stream_id?: string | null;
  quality?: string | null;
  connection_state: string;
}

export interface Device {
  id: number;
  name: string;
  location: string;
  ip_address: string;
  /** Edge 节点主机 IP/主机名，用于零配置发现，无需在 Edge 端配置 */
  edge_host?: string | null;
  status: DeviceStatus;
  last_heartbeat: string | null;
  device_token?: string;
  calibration_config?: string;
  created_at: string;
  updated_at: string;
  /** 视频流状态（设备列表接口 include_stream_status=true 时返回） */
  stream_status?: DeviceStreamStatus | null;
}

export interface CreateDeviceParams {
  name: string;
  location: string;
  ip_address: string;
  edge_host?: string;
}

export interface UpdateDeviceParams {
  name?: string;
  location?: string;
  ip_address?: string;
  edge_host?: string;
  status?: DeviceStatus;
}

// Alert Types
export type AlertType =
  | 'fire_violation'
  | 'smoke_violation'
  | 'ppe_violation'
  | 'distance_violation'
  | 'access_control';

export type AlertSeverity = 'CRITICAL' | 'DANGER' | 'WARNING';

export interface Alert {
  id: number;
  device_id: number;
  device_name?: string;
  type: AlertType;
  severity: AlertSeverity;
  message: string;
  metadata?: Record<string, any>;
  timestamp: string;
  image_url?: string;
  is_acknowledged: boolean;
  acknowledged_by?: number;
  acknowledged_at?: string;
}

export interface AlertFilterParams {
  skip?: number;
  limit?: number;
  device_id?: number;
  type?: AlertType;
  severity?: AlertSeverity;
  is_acknowledged?: boolean;
  start_date?: string;
  end_date?: string;
}

export interface AlertStats {
  total_alerts: number;
  by_type: Record<AlertType, number>;
  by_severity: Record<AlertSeverity, number>;
  unacknowledged_count: number;
  trend_24h: Array<{ hour: string; count: number }>;
}

// Task Types
export interface Task {
  id: number;
  title: string;
  description?: string;
  status: 'pending' | 'in_progress' | 'completed';
  priority: 'high' | 'medium' | 'low';
  assigned_to?: number;
  assignee_name?: string;
  due_date?: string;
  created_at: string;
  updated_at: string;
}

export interface CreateTaskParams {
  title: string;
  description?: string;
  status?: 'pending' | 'in_progress' | 'completed';
  priority?: 'high' | 'medium' | 'low';
  assigned_to?: number;
  due_date?: string;
}

export interface UpdateTaskParams extends Partial<CreateTaskParams> {}

export interface TaskFilterParams {
  skip?: number;
  limit?: number;
  status?: 'pending' | 'in_progress' | 'completed';
  assignee_id?: number;
}

// Video Streaming Types (WHEP 模式)
export interface StreamOffer {
  stream_id: string;
  whep_url: string;
  sdp?: string;
  type: 'offer';
  websocket_url?: string;
}

export interface StreamAnswer {
  sdp: string;
  type: 'answer';
}

export interface StreamStatus {
  device_id: number;
  is_active: boolean;
  stream_id?: string;
  quality?: 'low' | 'medium' | 'high';
  detection_overlay_enabled: boolean;
  connection_state: 'connecting' | 'connected' | 'disconnected' | 'failed';
  error?: string;
  /** 用于组件直接使用，避免重复请求 */
  offer?: StreamOffer;
}

export interface StreamControlParams {
  device_id: number;
  action: 'start' | 'stop' | 'toggle_overlay' | 'set_quality';
  quality?: 'low' | 'medium' | 'high';
  enable_overlay?: boolean;
}