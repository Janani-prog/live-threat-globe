import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Area,
  AreaChart,
} from "recharts";
import { useStats } from "../context/StatsContext";
import { categoryLabel } from "../lib/categories";
import { RISK_COLORS } from "../lib/risk";

const AXIS_COLOR = "#b9cbc1"; // on-surface-variant
const GRID_COLOR = "#3a4a43"; // outline-variant
const TOOLTIP_STYLE = {
  background: "rgba(26,26,26,0.95)",
  border: `1px solid ${GRID_COLOR}`,
  borderRadius: 0,
  fontFamily: "'JetBrains Mono', monospace",
  fontSize: 12,
};

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="hud-panel p-4 flex-1 min-w-[280px]">
      <h3 className="text-[11px] font-bold uppercase tracking-widest text-primary-fixed-dim mb-3">
        {title}
      </h3>
      {children}
    </div>
  );
}

function EmptyState() {
  return <p className="text-xs text-on-surface-variant opacity-60 py-8 text-center">No data yet</p>;
}

export function StatsDashboard() {
  const { summary, timeseries } = useStats();

  const countryData = summary?.top_countries.slice(0, 8) ?? [];
  const categoryData =
    summary?.category_breakdown.slice(0, 8).map((c) => ({ ...c, label: categoryLabel(c.key) })) ?? [];
  const timeseriesData =
    timeseries?.points.map((p) => ({
      time: new Date(p.bucket).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      count: p.count,
    })) ?? [];

  return (
    <section className="fixed top-24 left-4 right-4 bottom-20 z-20 overflow-y-auto pointer-events-auto">
      <div className="flex flex-col gap-4 max-w-5xl mx-auto">
        <Panel title="Events / Minute (last 60m)">
          {timeseriesData.length > 0 ? (
            <ResponsiveContainer width="100%" height={180}>
              <AreaChart data={timeseriesData}>
                <CartesianGrid stroke={GRID_COLOR} strokeDasharray="2 4" vertical={false} />
                <XAxis dataKey="time" stroke={AXIS_COLOR} fontSize={10} tickLine={false} />
                <YAxis stroke={AXIS_COLOR} fontSize={10} allowDecimals={false} tickLine={false} />
                <Tooltip contentStyle={TOOLTIP_STYLE} labelStyle={{ color: AXIS_COLOR }} />
                <Area
                  type="monotone"
                  dataKey="count"
                  stroke={RISK_COLORS.medium}
                  fill={RISK_COLORS.medium}
                  fillOpacity={0.15}
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <EmptyState />
          )}
        </Panel>

        <div className="flex flex-wrap gap-4">
          <Panel title="Top Countries">
            {countryData.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={countryData} layout="vertical" margin={{ left: 8 }}>
                  <CartesianGrid stroke={GRID_COLOR} strokeDasharray="2 4" horizontal={false} />
                  <XAxis type="number" stroke={AXIS_COLOR} fontSize={10} allowDecimals={false} tickLine={false} />
                  <YAxis dataKey="key" type="category" stroke={AXIS_COLOR} fontSize={10} width={40} tickLine={false} />
                  <Tooltip contentStyle={TOOLTIP_STYLE} labelStyle={{ color: AXIS_COLOR }} />
                  <Bar dataKey="count" fill={RISK_COLORS.medium} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <EmptyState />
            )}
          </Panel>

          <Panel title="Category Breakdown">
            {categoryData.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={categoryData} layout="vertical" margin={{ left: 8 }}>
                  <CartesianGrid stroke={GRID_COLOR} strokeDasharray="2 4" horizontal={false} />
                  <XAxis type="number" stroke={AXIS_COLOR} fontSize={10} allowDecimals={false} tickLine={false} />
                  <YAxis
                    dataKey="label"
                    type="category"
                    stroke={AXIS_COLOR}
                    fontSize={10}
                    width={90}
                    tickLine={false}
                  />
                  <Tooltip contentStyle={TOOLTIP_STYLE} labelStyle={{ color: AXIS_COLOR }} />
                  <Bar dataKey="count" fill={RISK_COLORS.high} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <EmptyState />
            )}
          </Panel>
        </div>
      </div>
    </section>
  );
}
