import { Badge } from "./ui/badge";
import { Info } from "lucide-react";
import { Tooltip, TooltipContent, TooltipTrigger } from "./ui/tooltip";

export default function DemoBadge() {
  return (
    <Tooltip delayDuration={0}>
      <TooltipTrigger asChild>
        <Badge 
          variant="outline" 
          className="bg-purple-50 text-purple-700 border-purple-200 cursor-help"
        >
          <Info className="w-3 h-3 mr-1" />
          Demo Data
        </Badge>
      </TooltipTrigger>
      <TooltipContent className="max-w-xs">
        <p className="text-xs">
          This system uses simulated data for demonstration purposes. 
          All workflows and features are functional but data is scripted and deterministic.
        </p>
      </TooltipContent>
    </Tooltip>
  );
}