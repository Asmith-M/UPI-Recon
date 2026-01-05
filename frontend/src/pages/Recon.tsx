import { useState, useEffect } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { ScrollArea } from "../components/ui/scroll-area";
import { Loader2, CheckCircle2, Clock } from "lucide-react";
import { apiClient } from "../lib/api";
import { useToast } from "../hooks/use-toast";
import CycleSelector from "../components/CycleSelector";
import DirectionSelector from "../components/DirectionSelector";

export default function Recon() {
  const { toast } = useToast();
  const [report, setReport] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [reconciliating, setReconciliating] = useState(false);
  const [summary, setSummary] = useState<any>(null);
  const [selectedCycle, setSelectedCycle] = useState("all");
  const [selectedDirection, setSelectedDirection] = useState("inward");

  useEffect(() => {
    fetchReconData();
  }, []);

  const fetchReconData = async () => {
    try {
      setLoading(true);
      // Fetch summary
      const summaryData = await apiClient.getSummary();
      setSummary(summaryData);

      // Fetch report
      const reportText = await apiClient.downloadLatestReport();
      const text = await reportText.text();
      setReport(text);
    } catch (error: any) {
      console.log("No reconciliation data yet");
      setReport(
        "No reconciliation data available yet. Run reconciliation to see results."
      );
      setSummary({
        run_id: null,
        generated_at: "",
        totals: { count: 0, amount: 0 },
        matched: { count: 0, amount: 0 },
        unmatched: { count: 0, amount: 0 },
        hanging: { count: 0, amount: 0 },
        exceptions: { count: 0, amount: 0 },
        status: "no_reconciliation_run",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleRunRecon = async () => {
    try {
      setReconciliating(true);
      const result = await apiClient.runReconciliation(undefined, selectedDirection);

      toast({
        title: "Reconciliation completed",
        description: `Processed ${result.matched_count} matched transactions`,
      });

      // Refresh data
      await fetchReconData();
    } catch (error: any) {
      toast({
        title: "Reconciliation failed",
        description: error.message || "An error occurred during reconciliation",
        variant: "destructive",
      });
    } finally {
      setReconciliating(false);
    }
  };

  const handleDownloadReport = async () => {
    try {
      const reportBlob = await apiClient.downloadLatestReport();
      const url = window.URL.createObjectURL(reportBlob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'reconciliation_report.txt';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast({
        title: "Report downloaded",
        description: "reconciliation_report.txt"
      });
    } catch (error: any) {
      toast({
        title: "Download failed",
        description: error.message || "Could not download report",
        variant: "destructive"
      });
    }
  };

  const handleDownloadAdjustments = async () => {
    try {
      const adjustmentsBlob = await apiClient.downloadLatestAdjustments();
      const url = window.URL.createObjectURL(adjustmentsBlob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'adjustments.csv';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast({
        title: "Adjustments downloaded",
        description: "adjustments.csv"
      });
    } catch (error: any) {
      toast({
        title: "Download failed",
        description: error.message || "Could not download adjustments",
        variant: "destructive"
      });
    }
  };

  const handleRefreshReport = async () => {
    try {
      await fetchReconData();
      toast({
        title: "Report refreshed",
        description: "Latest report loaded"
      });
    } catch (error: any) {
      toast({
        title: "Refresh failed",
        description: error.message || "Could not refresh report",
        variant: "destructive"
      });
    }
  };
  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Recon Workflow</h1>
        <p className="text-muted-foreground">
          Run reconciliation and view reports
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6">
        {/* Status Banner */}
        {summary && summary.run_id && (
          <Card className="shadow-lg bg-gradient-to-r from-blue-50 to-card border-blue-200">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-lg">
                    Current Reconciliation Status
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    Run ID: {summary.run_id}
                  </p>
                  <div className="flex items-center gap-1 text-sm text-muted-foreground">
                    <span>Status:</span>
                    {reconciliating ? (
                      <span className="flex items-center gap-1">
                        <Clock className="h-4 w-4 animate-pulse" /> Running...
                      </span>
                    ) : summary.status === "completed" ? (
                      <span className="flex items-center gap-1 text-green-600">
                        <CheckCircle2 className="h-4 w-4" /> Completed
                      </span>
                    ) : (
                      <span>{summary.status}</span>
                    )}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-3xl font-bold text-green-600">
                    {summary.matched?.count ?? summary.matched ?? 0}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    Transactions Matched
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Run Reconciliation Section */}
        <Card className="shadow-lg">
          <CardHeader>
            <CardTitle>Run Reconciliation</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Cycle</Label>
                <CycleSelector value={selectedCycle} onValueChange={setSelectedCycle} />
              </div>
              <div className="space-y-2">
                <Label>Direction</Label>
                <DirectionSelector value={selectedDirection} onValueChange={setSelectedDirection} />
              </div>
            </div>
            <p className="text-sm text-muted-foreground">
              Select cycle and direction, then click the button below to run reconciliation
            </p>
            <Button
              className="w-full rounded-full py-6 bg-brand-blue hover:bg-brand-mid shadow-lg"
              onClick={handleRunRecon}
              disabled={reconciliating}
            >
              {reconciliating ? (
                <>
                  <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                  Running Reconciliation...
                </>
              ) : (
                "Run Recon"
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Summary Cards */}
        {summary && (
          <div className="grid grid-cols-4 gap-4">
            <Card className="shadow-lg">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Total Transactions
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold">
                  {summary.totals?.count ?? summary.total_transactions ?? 0}
                </p>
              </CardContent>
            </Card>

            <Card className="shadow-lg">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Matched
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold text-green-600">
                  {summary.matched?.count ?? summary.matched ?? 0}
                </p>
              </CardContent>
            </Card>

            <Card className="shadow-lg">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Unmatched
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold text-red-600">
                  {summary.unmatched?.count ?? summary.unmatched ?? 0}
                </p>
              </CardContent>
            </Card>

            <Card className="shadow-lg">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Adjustments
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold">{summary.exceptions?.amount ?? summary.adjustments ?? 0}</p>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Report Display */}
        <Card className="shadow-lg">
          <CardHeader>
            <CardTitle>Reconciliation Report</CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-96 border rounded-lg p-4 bg-muted/20">
              <pre className="text-sm font-mono whitespace-pre-wrap">
                {loading ? "Loading report..." : report}
              </pre>
            </ScrollArea>
            <div className="flex gap-4 justify-end mt-4">
              <Button 
                variant="outline" 
                className="rounded-full"
                onClick={handleRefreshReport}
              >
                Refresh Report
              </Button>
              <Button 
                className="rounded-full bg-brand-blue hover:bg-brand-mid"
                onClick={handleDownloadReport}
              >
                Download Report (TXT)
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Download Adjustments */}
        <Card className="shadow-lg">
          <CardHeader>
            <CardTitle>Download Adjustments</CardTitle>
          </CardHeader>
          <CardContent>
            <Button 
              className="w-full rounded-full py-6 bg-brand-blue hover:bg-brand-mid shadow-lg"
              onClick={handleDownloadAdjustments}
            >
              Download adjustments.csv
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
