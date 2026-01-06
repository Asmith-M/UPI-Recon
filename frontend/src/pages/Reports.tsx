import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { FileText, Download, Loader2 } from "lucide-react";
import { apiClient } from "../lib/api";
import { useToast } from "../hooks/use-toast";
import { AxiosResponse } from "axios";

interface ReportType {
  id: string;
  name: string;
  description: string;
  endpoint: string;
}

const reportTypes: ReportType[] = [
  // JSON Reports
  { 
    id: "matched",
    name: "Matched Transactions (JSON)", 
    description: "All successfully matched transactions across CBS, Switch, and NPCI",
    endpoint: "matched"
  },
  { 
    id: "unmatched",
    name: "Unmatched Transactions (JSON)", 
    description: "Transactions that couldn't be matched - includes partial matches and orphans",
    endpoint: "unmatched"
  },
  { 
    id: "summary",
    name: "Reconciliation Summary (JSON)", 
    description: "Complete summary with statistics and breakdown of all transaction categories",
    endpoint: "summary"
  },
  
  // CSV Reports
  { 
    id: "matched_csv",
    name: "Matched Transactions (CSV)", 
    description: "Matched transactions in CSV format for Excel import",
    endpoint: "matched/csv"
  },
  { 
    id: "unmatched_csv",
    name: "Unmatched Transactions (CSV)", 
    description: "Unmatched transactions in CSV format for Excel import",
    endpoint: "unmatched/csv"
  },
  
  // TTUM Reports
  { 
    id: "ttum",
    name: "TTUM Report (ZIP)", 
    description: "Transaction Type Unmatched Report - all TTUM files packaged together",
    endpoint: "ttum"
  },
  { 
    id: "ttum_csv",
    name: "TTUM Report (CSV)", 
    description: "TTUM data in CSV format for detailed analysis",
    endpoint: "ttum/csv"
  },
  { 
    id: "ttum_xlsx",
    name: "TTUM Report (XLSX)", 
    description: "TTUM data in Excel format with formatting",
    endpoint: "ttum/xlsx"
  },
  
  // Other Reports
  { 
    id: "adjustments",
    name: "Adjustments (CSV)", 
    description: "CSV file containing all adjustments and force-match candidates",
    endpoint: "adjustments"
  },
  { 
    id: "report",
    name: "Text Report (TXT)", 
    description: "Human-readable text report with detailed reconciliation breakdown",
    endpoint: "report"
  },
];

const downloadFile = (response: AxiosResponse<Blob>, defaultFilename: string) => {
  const blob = response.data;
  const contentDisposition = response.headers['content-disposition'];
  let filename = defaultFilename;

  if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename="?(.+)"?/);
      if (filenameMatch && filenameMatch.length > 1) {
          filename = filenameMatch[1];
      }
  }

  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(url);
}

export default function Reports() {
  const { toast } = useToast();
  const [loadingReports, setLoadingReports] = useState<Record<string, boolean>>({});

  const handleDownloadReport = async (report: ReportType) => {
    try {
      setLoadingReports(prev => ({ ...prev, [report.id]: true }));

      // Handle JSON reports separately
      if (!report.endpoint.includes('/') && !['ttum', 'report', 'adjustments'].includes(report.id)) {
        const data = await apiClient.getReport(report.endpoint);
        
        const jsonStr = JSON.stringify(data, null, 2);
        const blob = new Blob([jsonStr], { type: 'application/json' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${report.id}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
      } else {
        // Handle file downloads
        let response: AxiosResponse<Blob>;
        let defaultFilename = 'download';

        if (report.id === "adjustments") {
          response = await apiClient.downloadLatestAdjustments();
          defaultFilename = 'adjustments.csv';
        } else if (report.id === "report") {
          response = await apiClient.downloadLatestReport();
          defaultFilename = 'reconciliation_report.txt';
        } else {
          response = await apiClient.downloadReport(report.endpoint);
          const extension = report.endpoint.split('/').pop();
          defaultFilename = `${report.id}.${extension}`;
        }
        
        downloadFile(response, defaultFilename);
      }

      toast({
        title: "Success",
        description: `${report.name} downloaded successfully`
      });

    } catch (error: any) {
      toast({
        title: "Error",
        description: error.message || "Failed to download report. Please try again.",
        variant: "destructive"
      });
    } finally {
      setLoadingReports(prev => ({ ...prev, [report.id]: false }));
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Reports</h1>
        <p className="text-muted-foreground">Generate and download reconciliation reports</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {reportTypes.map((report) => (
          <Card key={report.id} className="shadow-lg hover:shadow-xl transition-shadow">
            <CardHeader>
              <CardTitle className="flex items-center gap-3">
                <FileText className="w-5 h-5 text-brand-blue" />
                {report.name}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground mb-4">{report.description}</p>
              <Button 
                className="w-full rounded-full bg-brand-blue hover:bg-brand-mid"
                onClick={() => handleDownloadReport(report)}
                disabled={loadingReports[report.id]}
              >
                {loadingReports[report.id] ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Downloading...
                  </>
                ) : (
                  <>
                    <Download className="w-4 h-4 mr-2" />
                    Download Report
                  </>
                )}
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
