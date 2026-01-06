import { useState, useEffect } from "react";
import { Card, CardContent } from "./ui/card";
import { Button } from "./ui/button";
import { Calendar, RefreshCw } from "lucide-react";

interface DateFilterProps {
  onDateChange?: (dateFrom: string, dateTo: string) => void;
  onRefresh?: () => void;
  showRefresh?: boolean;
  className?: string;
}

export default function DateFilter({
  onDateChange,
  onRefresh,
  showRefresh = true,
  className = ""
}: DateFilterProps) {
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  // Set default dates to current month
  useEffect(() => {
    const now = new Date();
    const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
    const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0);

    const formatDate = (date: Date) => date.toISOString().split('T')[0];

    setDateFrom(formatDate(firstDay));
    setDateTo(formatDate(lastDay));
  }, []);

  const handleDateChange = (from: string, to: string) => {
    setDateFrom(from);
    setDateTo(to);
    if (onDateChange) {
      onDateChange(from, to);
    }
  };

  const handleRefresh = () => {
    if (onRefresh) {
      onRefresh();
    }
  };

  const setToday = () => {
    const today = new Date().toISOString().split('T')[0];
    handleDateChange(today, today);
  };

  const setThisWeek = () => {
    const now = new Date();
    const startOfWeek = new Date(now.setDate(now.getDate() - now.getDay()));
    const endOfWeek = new Date(now.setDate(now.getDate() - now.getDay() + 6));

    const formatDate = (date: Date) => date.toISOString().split('T')[0];
    handleDateChange(formatDate(startOfWeek), formatDate(endOfWeek));
  };

  const setThisMonth = () => {
    const now = new Date();
    const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
    const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0);

    const formatDate = (date: Date) => date.toISOString().split('T')[0];
    handleDateChange(formatDate(firstDay), formatDate(lastDay));
  };

  return (
    <Card className={`shadow-sm ${className}`}>
      <CardContent className="pt-4">
        <div className="space-y-4">
          {/* Quick Date Buttons */}
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={setToday}
              className="text-xs"
            >
              Today
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={setThisWeek}
              className="text-xs"
            >
              This Week
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={setThisMonth}
              className="text-xs"
            >
              This Month
            </Button>
            {showRefresh && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleRefresh}
                className="text-xs gap-1"
              >
                <RefreshCw className="w-3 h-3" />
                Refresh
              </Button>
            )}
          </div>

          {/* Date Range Inputs */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4 text-muted-foreground" />
              <span className="text-sm font-medium">Date Range:</span>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => handleDateChange(e.target.value, dateTo)}
                className="px-3 py-1 border rounded-md text-sm bg-background"
              />
              <span className="text-sm text-muted-foreground">to</span>
              <input
                type="date"
                value={dateTo}
                onChange={(e) => handleDateChange(dateFrom, e.target.value)}
                className="px-3 py-1 border rounded-md text-sm bg-background"
              />
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
