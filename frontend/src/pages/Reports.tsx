import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { FileText, Download, Loader2 } from "lucide-react";
import { apiClient } from "../lib/api";
import { useToast } from "../hooks/use-toast";
import { AxiosResponse } from "axios";

interface ReportType {
  id: string;
  name: string;
  description: string;
  endpoint: string;
  category?: string;
}

// Listing Reports - Raw ingestion files
const listingReports: ReportType[] = [
  { 
    id: "cbs_beneficiary",
    name: "CBS Beneficiary (Raw)", 
    description: "Raw beneficiary data from CBS",
    endpoint: "cbs_beneficiary",
    category: "listing"
  },
  { 
    id: "cbs_remitter",
    name: "CBS Remitter (Raw)", 
    description: "Raw remitter data from CBS",
    endpoint: "cbs_remitter",
    category: "listing"
  },
  { 
    id: "switch_inward",
    name: "Switch Inward (Raw)", 
    description: "Raw inward transaction data from Switch",
    endpoint: "switch_inward",
    category: "listing"
  },
  { 
    id: "switch_outward",
    name: "Switch Outward (Raw)", 
    description: "Raw outward transaction data from Switch",
    endpoint: "switch_outward",
    category: "listing"
  },
  { 
    id: "npci_inward",
    name: "NPCI Inward (Raw)", 
    description: "Raw inward transaction data from NPCI",
    endpoint: "npci_inward",
    category: "listing"
  },
  { 
    id: "npci_outward",
    name: "NPCI Outward (Raw)", 
    description: "Raw outward transaction data from NPCI",
    endpoint: "npci_outward",
    category: "listing"
  },
];

// Reconciliation Reports - Categorized by type and direction
const reconReportsInward: ReportType[] = [
  {
    id: "gl_vs_switch_matched_inward",
    name: "GL vs. Switch - Matched",
    description: "Inward transactions matched between GL and Switch",
    endpoint: "recon/gl_vs_switch/matched/inward",
    category: "recon_inward"
  },
  {
    id: "gl_vs_switch_unmatched_inward",
    name: "GL vs. Switch - Unmatched (with Ageing)",
    description: "Inward transactions unmatched between GL and Switch with aging analysis",
    endpoint: "recon/gl_vs_switch/unmatched/inward",
    category: "recon_inward"
  },
  {
    id: "switch_vs_network_matched_inward",
    name: "Switch vs. Network - Matched",
    description: "Inward transactions matched between Switch and Network",
    endpoint: "recon/switch_vs_network/matched/inward",
    category: "recon_inward"
  },
  {
    id: "switch_vs_network_unmatched_inward",
    name: "Switch vs. Network - Unmatched (with Ageing)",
    description: "Inward transactions unmatched between Switch and Network with aging analysis",
    endpoint: "recon/switch_vs_network/unmatched/inward",
    category: "recon_inward"
  },
  {
    id: "gl_vs_network_matched_inward",
    name: "GL vs. Network - Matched",
    description: "Inward transactions matched between GL and Network",
    endpoint: "recon/gl_vs_network/matched/inward",
    category: "recon_inward"
  },
  {
    id: "gl_vs_network_unmatched_inward",
    name: "GL vs. Network - Unmatched (with Ageing)",
    description: "Inward transactions unmatched between GL and Network with aging analysis",
    endpoint: "recon/gl_vs_network/unmatched/inward",
    category: "recon_inward"
  },
  {
    id: "hanging_transactions_inward",
    name: "Hanging Transactions",
    description: "Inward transactions stuck in intermediate state",
    endpoint: "recon/hanging_transactions/inward",
    category: "recon_inward"
  },
];

const reconReportsOutward: ReportType[] = [
  {
    id: "gl_vs_switch_matched_outward",
    name: "GL vs. Switch - Matched",
    description: "Outward transactions matched between GL and Switch",
    endpoint: "recon/gl_vs_switch/matched/outward",
    category: "recon_outward"
  },
  {
    id: "gl_vs_switch_unmatched_outward",
    name: "GL vs. Switch - Unmatched (with Ageing)",
    description: "Outward transactions unmatched between GL and Switch with aging analysis",
    endpoint: "recon/gl_vs_switch/unmatched/outward",
    category: "recon_outward"
  },
  {
    id: "switch_vs_network_matched_outward",
    name: "Switch vs. Network - Matched",
    description: "Outward transactions matched between Switch and Network",
    endpoint: "recon/switch_vs_network/matched/outward",
    category: "recon_outward"
  },
  {
    id: "switch_vs_network_unmatched_outward",
    name: "Switch vs. Network - Unmatched (with Ageing)",
    description: "Outward transactions unmatched between Switch and Network with aging analysis",
    endpoint: "recon/switch_vs_network/unmatched/outward",
    category: "recon_outward"
  },
  {
    id: "gl_vs_network_matched_outward",
    name: "GL vs. Network - Matched",
    description: "Outward transactions matched between GL and Network",
    endpoint: "recon/gl_vs_network/matched/outward",
    category: "recon_outward"
  },
  {
    id: "gl_vs_network_unmatched_outward",
    name: "GL vs. Network - Unmatched (with Ageing)",
    description: "Outward transactions unmatched between GL and Network with aging analysis",
    endpoint: "recon/gl_vs_network/unmatched/outward",
    category: "recon_outward"
  },
  {
    id: "hanging_transactions_outward",
    name: "Hanging Transactions",
    description: "Outward transactions stuck in intermediate state",
    endpoint: "recon/hanging_transactions/outward",
    category: "recon_outward"
  },
];

// TTUM and Annexure Reports
const ttumAnnexureReports: ReportType[] = [
  {
    id: "ttum_consolidated",
    name: "Consolidated TTUM Report",
    description: "Complete TTUM report (Refund, Recovery, Auto-credit, etc.)",
    endpoint: "ttum",
    category: "ttum"
  },
  {
    id: "annexure_i_raw",
    name: "Annexure I (Raw)",
    description: "Raw Annexure I data for detailed review",
    endpoint: "annexure/i/raw",
    category: "ttum"
  },
  {
    id: "annexure_ii_raw",
    name: "Annexure II (Raw)",
    description: "Raw Annexure II data for detailed review",
    endpoint: "annexure/ii/raw",
    category: "ttum"
  },
  {
    id: "annexure_iii_adjustment",
    name: "Annexure III (Adjustment Report)",
    description: "Adjustment report with reconciliation details",
    endpoint: "annexure/iii/adjustment",
    category: "ttum"
  },
  {
    id: "annexure_iv_bulk",
    name: "Annexure IV (Bulk Upload)",
    description: "Bulk upload format for system import",
    endpoint: "annexure/iv/bulk",
    category: "ttum"
  },
];

// Legacy reports (keep for backward compatibility)
const reportTypes: ReportType[] = [
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
        } else if (report.id === "ttum" || report.id === "ttum_consolidated") {
          response = await apiClient.downloadReport(report.endpoint);
          defaultFilename = 'ttum_report.zip';
        } else if (report.id === "ttum_csv") {
          response = await apiClient.downloadTTUMCSV();
          defaultFilename = 'ttum_data.csv';
        } else if (report.id === "ttum_xlsx") {
          response = await apiClient.downloadTTUMXLSX();
          defaultFilename = 'ttum_data.xlsx';
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

  const ReportCard = ({ report }: { report: ReportType }) => (
    <Card className="shadow-lg hover:shadow-xl transition-shadow">
      <CardHeader>
        <CardTitle className="flex items-center gap-3 text-base">
          <FileText className="w-5 h-5 text-brand-blue" />
          {report.name}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground mb-4">{report.description}</p>
        <Button 
          className="w-full rounded-full bg-brand-blue hover:bg-brand-mid text-sm"
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
              Download
            </>
          )}
        </Button>
      </CardContent>
    </Card>
  );

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Reports</h1>
        <p className="text-muted-foreground">Generate and download reconciliation reports</p>
      </div>

      <Tabs defaultValue="listing" className="w-full">
        <TabsList className="bg-muted/30 grid w-full grid-cols-4">
          <TabsTrigger value="listing" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
            Listing
          </TabsTrigger>
          <TabsTrigger value="recon" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
            Reconciliation
          </TabsTrigger>
          <TabsTrigger value="ttum" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
            TTUM & Annexure
          </TabsTrigger>
          <TabsTrigger value="legacy" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
            Legacy
          </TabsTrigger>
        </TabsList>

        {/* Listing Reports Tab */}
        <TabsContent value="listing" className="space-y-6 mt-6">
          <Card className="bg-blue-50 border border-blue-200">
            <CardContent className="pt-6">
              <p className="text-sm text-blue-900">
                <strong>Pre-Reconciliation Listing:</strong> Download raw ingestion files for the 6 core data sources: CBS Beneficiary, CBS Remitter, Switch (In/Out), and NPCI (In/Out).
              </p>
            </CardContent>
          </Card>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {listingReports.map((report) => (
              <ReportCard key={report.id} report={report} />
            ))}
          </div>
        </TabsContent>

        {/* Reconciliation Reports Tab */}
        <TabsContent value="recon" className="space-y-6 mt-6">
          <Tabs defaultValue="inward" className="w-full">
            <TabsList className="bg-muted/20">
              <TabsTrigger value="inward" className="data-[state=active]:bg-secondary data-[state=active]:text-secondary-foreground">
                Inward Direction
              </TabsTrigger>
              <TabsTrigger value="outward" className="data-[state=active]:bg-secondary data-[state=active]:text-secondary-foreground">
                Outward Direction
              </TabsTrigger>
            </TabsList>

            {/* Inward Reports */}
            <TabsContent value="inward" className="space-y-6 mt-6">
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <p className="text-sm text-green-900">
                  <strong>Inward Transactions:</strong> Reconciliation reports for credit/inward transactions with 3 comparison pairs (GL vs Switch, Switch vs Network, GL vs Network) plus Hanging Transactions.
                </p>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {reconReportsInward.map((report) => (
                  <ReportCard key={report.id} report={report} />
                ))}
              </div>
            </TabsContent>

            {/* Outward Reports */}
            <TabsContent value="outward" className="space-y-6 mt-6">
              <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
                <p className="text-sm text-orange-900">
                  <strong>Outward Transactions:</strong> Reconciliation reports for debit/outward transactions with 3 comparison pairs (GL vs Switch, Switch vs Network, GL vs Network) plus Hanging Transactions.
                </p>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {reconReportsOutward.map((report) => (
                  <ReportCard key={report.id} report={report} />
                ))}
              </div>
            </TabsContent>
          </Tabs>
        </TabsContent>

        {/* TTUM & Annexure Tab */}
        <TabsContent value="ttum" className="space-y-6 mt-6">
          <Card className="bg-purple-50 border border-purple-200">
            <CardContent className="pt-6">
              <p className="text-sm text-purple-900">
                <strong>TTUM & Annexures:</strong> Download consolidated TTUM report (Refund, Recovery, Auto-credit, etc.) and Annexure files (I-Raw, II-Raw, III-Adjustment, IV-Bulk).
              </p>
            </CardContent>
          </Card>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {ttumAnnexureReports.map((report) => (
              <ReportCard key={report.id} report={report} />
            ))}
          </div>
        </TabsContent>

        {/* Legacy Reports Tab */}
        <TabsContent value="legacy" className="space-y-6 mt-6">
          <Card className="bg-gray-50 border border-gray-200">
            <CardContent className="pt-6">
              <p className="text-sm text-gray-700">
                <strong>Legacy Reports:</strong> Standard reconciliation reports for backward compatibility.
              </p>
            </CardContent>
          </Card>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {reportTypes.map((report) => (
              <ReportCard key={report.id} report={report} />
            ))}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
