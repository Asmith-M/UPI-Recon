import axios, { AxiosInstance, AxiosResponse } from 'axios';

// API Base Configuration
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// Create axios instance with default config
const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 seconds for file uploads
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for adding auth headers if needed
api.interceptors.request.use(
  (config) => {
    // Add auth headers here if needed
    // const token = localStorage.getItem('authToken');
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`;
    // }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized access
      console.error('Unauthorized access');
    } else if (error.response?.status >= 500) {
      // Handle server errors
      console.error('Server error:', error.response.data);
    }
    return Promise.reject(error);
  }
);

// TypeScript interfaces for API responses
export interface UploadResponse {
  status: string;
  message: string;
  run_id: string;
  folder: string;
  cbs_balance?: string;
  transaction_date?: string;
  next_step?: string;
}

export interface ReconciliationResponse {
  status: string;
  run_id: string;
  output_folder: string;
  matched_count: number;
  unmatched_count: number;
  exception_count: number;
  partial_match_count: number;
  orphan_count: number;
}

export interface SummaryResponse {
  total_transactions: number;
  matched: number;
  unmatched: number;
  adjustments: number;
  status: string;
  run_id: string;
}

export interface ReportResponse {
  report_type: string;
  data?: any;
  count?: number;
  message?: string;
}

export interface ChatbotResponse {
  rrn?: string;
  details?: any;
  run_id?: string;
}

export interface ForceMatchResponse {
  status: string;
  message: string;
  action: string;
  rrn: string;
}

export interface RawDataResponse {
  run_id: string;
  data: any;
  summary: {
    total_rrns: number;
    matched_count: number;
    unmatched_count: number;
    exception_count: number;
    file_path: string;
  };
}

// API Functions
export const apiClient = {
  // File Upload
  uploadFiles: async (files: {
    cbs_inward: File;
    cbs_outward: File;
    switch: File;
    npci_inward: File;
    npci_outward: File;
    ntsl: File;
    adjustment: File;
    cbs_balance?: string;
    transaction_date?: string;
  }): Promise<UploadResponse> => {
    const formData = new FormData();
    Object.entries(files).forEach(([key, file]) => {
      if (file instanceof File) {
        formData.append(key, file);
      } else if (file) {
        formData.append(key, file);
      }
    });

    const response: AxiosResponse<UploadResponse> = await api.post('/api/v1/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Reconciliation
  runReconciliation: async (direction: string = 'INWARD'): Promise<ReconciliationResponse> => {
    const response: AxiosResponse<ReconciliationResponse> = await api.post('/api/v1/recon/run', null, {
      params: { direction },
    });
    return response.data;
  },

  // Summary
  getSummary: async (): Promise<SummaryResponse> => {
    const response: AxiosResponse<SummaryResponse> = await api.get('/api/v1/summary');
    return response.data;
  },

  // Historical Summary for Charts
  getHistoricalSummary: async (): Promise<any[]> => {
    const response: AxiosResponse<any[]> = await api.get('/api/v1/summary/historical');
    return response.data;
  },

  // Reports
  getReport: async (reportType: string): Promise<ReportResponse> => {
    const response: AxiosResponse<ReportResponse> = await api.get(`/api/v1/reports/${reportType}`);
    return response.data;
  },

  // Chatbot/Enquiry - Now directly integrated in main app
  getChatbotByRRN: async (rrn: string): Promise<ChatbotResponse> => {
    // Backend expects a query param `rrn` on /api/v1/chatbot
    const response: AxiosResponse<any> = await api.get('/api/v1/chatbot', { params: { rrn } });
    const data = response.data;

    // Normalize backend response into the ChatbotResponse shape expected by frontend
    return {
      rrn: data?.rrn || rrn,
      details: data || null,
      run_id: data?.recon_run_id || data?.run_id || undefined,
    };
  },

  getChatbotByTxnId: async (txnId: string): Promise<ChatbotResponse> => {
    const response: AxiosResponse<any> = await api.get('/api/v1/chatbot', {
      params: { txn_id: txnId },
    });
    const data = response.data;

    // Normalize backend response into the ChatbotResponse shape expected by frontend
    return {
      rrn: data?.rrn || undefined,
      details: data || null,
      run_id: data?.recon_run_id || data?.run_id || undefined,
    };
  },

  // Force Match
  forceMatch: async (rrn: string, source1: string, source2: string, action: string = 'match'): Promise<ForceMatchResponse> => {
    const response: AxiosResponse<ForceMatchResponse> = await api.post('/api/v1/force-match', null, {
      params: { rrn, source1, source2, action },
    });
    return response.data;
  },

  // Auto Match Parameters
  setAutoMatchParameters: async (params: {
    amount_tolerance: number;
    date_tolerance_days: number;
    enable_auto_match: boolean;
  }): Promise<any> => {
    const response: AxiosResponse = await api.post('/api/v1/auto-match/parameters', null, {
      params: params
    });
    return response.data;
  },

  // Rollback
  rollbackReconciliation: async (runId?: string): Promise<any> => {
    const response: AxiosResponse = await api.post('/api/v1/rollback', null, {
      params: runId ? { run_id: runId } : {},
    });
    return response.data;
  },

  // Raw Data
  getRawData: async (): Promise<RawDataResponse> => {
    const response: AxiosResponse<RawDataResponse> = await api.get('/api/v1/recon/latest/raw');
    return response.data;
  },

  // File Downloads
  downloadLatestReport: async (): Promise<Blob> => {
    const response: AxiosResponse<Blob> = await api.get('/api/v1/recon/latest/report', {
      responseType: 'blob',
    });
    return response.data;
  },

  downloadLatestAdjustments: async (): Promise<Blob> => {
    const response: AxiosResponse<Blob> = await api.get('/api/v1/recon/latest/adjustments', {
      responseType: 'blob',
    });
    return response.data;
  },

  // Health Check
  healthCheck: async (): Promise<any> => {
    const response: AxiosResponse = await api.get('/health');
    return response.data;
  },
};

export default apiClient;
