import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { FileText, Download, Loader2 } from "lucide-react";
import { apiClient } from "../lib/api";
import { useToast } from "../hooks/use-toast";

interface ReportType {
  id: string;
  name: string;
  description: string;
  endpoint: string;
}

const reportTypes: ReportType[] = [
  { 
    id: "matched",
    name: "Matched Transactions Report", 
    description: "All successfully matched transactions across CBS, Switch, and NPCI",
    endpoint: "matched"
  },
  { 
    id: "unmatched",
    name: "Unmatched Transactions Report", 
    description: "Transactions that couldn't be matched - includes partial matches and orphans",
    endpoint: "unmatched"
  },
  { 
    id: "summary",
    name: "Reconciliation Summary Report", 
    description: "Complete summary with statistics and breakdown of all transaction categories",
    endpoint: "summary"
  },
  { 
    id: "ttum",
    name: "TTUM Report", 
    description: "Transaction Type Unmatched Report for detailed analysis",
    endpoint: "ttum"
  },
  { 
    id: "adjustments",
    name: "Adjustments CSV", 
    description: "CSV file containing all adjustments and force-match candidates",
    endpoint: "adjustments"
  },
  { 
    id: "report",
    name: "Text Report", 
    description: "Human-readable text report with detailed reconciliation breakdown",
    endpoint: "report"
  },
];

export default function Reports() {
  const { toast } = useToast();
  const [loadingReports, setLoadingReports] = useState<Record<string, boolean>>({});

  const handleDownloadReport = async (report: ReportType) => {
    try {
      setLoadingReports(prev => ({ ...prev, [report.id]: true }));

      if (report.id === "adjustments") {
        // Download CSV file
        const blob = await apiClient.downloadLatestAdjustments();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'adjustments.csv';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);

        toast({
          title: "Success",
          description: "Adjustments CSV downloaded successfully"
        });
      } else if (report.id === "report") {
        // Download text report
        const blob = await apiClient.downloadLatestReport();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'reconciliation_report.txt';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);

        toast({
          title: "Success",
          description: "Report downloaded successfully"
        });
      } else {
        // Get JSON report data
        const data = await apiClient.getReport(report.endpoint);
        
        // Convert to JSON and download
        const jsonStr = JSON.stringify(data, null, 2);
        const blob = new Blob([jsonStr], { type: 'application/json' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${report.id}_report.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);

        toast({
          title: "Success",
          description: `${report.name} downloaded successfully`
        });
      }
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
