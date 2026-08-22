import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ResultPayload } from "../types";

const currency = (n: number) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(n);

function Card({
  title,
  rows,
  accent = false,
}: {
  title: string;
  rows: { label: string; value: string }[];
  accent?: boolean;
}) {
  return (
    <div
      className={`flex-1 rounded-xl border p-5 ${
        accent
          ? "border-[var(--accent-strong)]/40 bg-[var(--accent-soft)]"
          : "border-[var(--ink)]/12 bg-white/60"
      }`}
    >
      <h3 className="mb-3 text-base font-semibold text-[var(--ink)]">{title}</h3>
      <dl className="space-y-2">
        {rows.map((r) => (
          <div key={r.label} className="flex items-baseline justify-between gap-4">
            <dt className="text-sm text-[var(--ink-muted)]">{r.label}</dt>
            <dd className="text-right text-sm font-medium text-[var(--ink)]">{r.value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

function SipPauseView({ output }: { output: any }) {
  const a = output.scenario_a;
  const b = output.scenario_b;
  const comparison = output.comparison;

  const chartData: { month: number; [key: string]: number }[] = [];
  const len = Math.max(a.loan_balance_over_time.length, b.loan_balance_over_time.length);
  for (let i = 0; i < len; i++) {
    chartData.push({
      month: i + 1,
      [a.label]: a.loan_balance_over_time[i] ?? 0,
      [b.label]: b.loan_balance_over_time[i] ?? 0,
    });
  }

  return (
    <>
      <div className="flex flex-col gap-4 sm:flex-row">
        <Card
          title={a.label}
          rows={[
            { label: "Total loan interest", value: currency(a.loan_total_interest) },
            { label: "Loan payoff (months)", value: `${a.loan_months_taken}` },
            { label: "Final SIP corpus", value: currency(a.sip_final_corpus) },
          ]}
        />
        <Card
          title={b.label}
          accent
          rows={[
            { label: "Total loan interest", value: currency(b.loan_total_interest) },
            { label: "Loan payoff (months)", value: `${b.loan_months_taken}` },
            { label: "Final SIP corpus", value: currency(b.sip_final_corpus) },
          ]}
        />
      </div>

      <div className="mt-4 rounded-xl border border-[var(--ink)]/12 bg-white/60 p-5">
        <h3 className="mb-3 text-base font-semibold text-[var(--ink)]">Loan balance over time</h3>
        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(36,26,18,0.12)" />
              <XAxis
                dataKey="month"
                tick={{ fontSize: 12, fill: "var(--ink-muted)" }}
                label={{ value: "Month", position: "insideBottom", offset: -4, fontSize: 12, fill: "var(--ink-muted)" }}
              />
              <YAxis
                tick={{ fontSize: 12, fill: "var(--ink-muted)" }}
                tickFormatter={(v) => currency(v)}
                width={90}
              />
              <Tooltip formatter={(v) => currency(Number(v))} />
              <Legend />
              <Line type="monotone" dataKey={a.label} stroke="#a3907a" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey={b.label} stroke="var(--accent-strong)" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <Card
        title="Net comparison"
        rows={[
          { label: "Loan interest saved", value: currency(comparison.loan_interest_saved) },
          { label: "Loan tenure reduced by", value: `${comparison.loan_tenure_reduced_months} months` },
          { label: "SIP corpus difference", value: currency(comparison.sip_corpus_difference) },
          { label: "Net financial difference", value: currency(comparison.net_financial_difference) },
        ]}
      />
    </>
  );
}

function EmiComparisonView({ output }: { output: any }) {
  const offers = output.offers as any[];
  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:flex-wrap">
      {offers.map((offer) => (
        <Card
          key={offer.label}
          title={offer.label}
          accent={offer.label === output.lowest_total_interest_offer}
          rows={[
            { label: "Principal", value: currency(offer.principal) },
            { label: "Interest rate", value: `${offer.annual_interest_rate_pct}%` },
            { label: "Tenure", value: `${offer.tenure_months} months` },
            { label: "EMI", value: currency(offer.emi) },
            { label: "Total interest", value: currency(offer.total_interest_paid) },
            { label: "Total repaid", value: currency(offer.total_amount_repaid) },
          ]}
        />
      ))}
    </div>
  );
}

function OpportunityCostView({ output }: { output: any }) {
  const prepay = output.prepayment_option;
  const invest = output.investment_option;
  return (
    <div className="flex flex-col gap-4 sm:flex-row">
      <Card
        title={prepay.label}
        rows={[
          { label: "Guaranteed interest saved", value: currency(prepay.guaranteed_interest_saved) },
          { label: "Risk", value: prepay.risk },
        ]}
      />
      <Card
        title={invest.label}
        accent
        rows={[
          { label: "Projected future value", value: currency(invest.projected_future_value) },
          { label: "Projected growth", value: currency(invest.projected_growth) },
          { label: "Risk", value: invest.risk },
        ]}
      />
    </div>
  );
}

export default function ResultView({ result }: { result: ResultPayload }) {
  const output = result.calculator_output;

  return (
    <div className="mx-auto w-full max-w-3xl">
      <p className="mb-5 whitespace-pre-line text-sm leading-relaxed text-[var(--ink)]">
        {result.explanation}
      </p>

      {result.scenario === "sip_pause_vs_loan_payoff" && <SipPauseView output={output} />}
      {result.scenario === "emi_comparison" && <EmiComparisonView output={output} />}
      {result.scenario === "opportunity_cost" && <OpportunityCostView output={output} />}

      <div className="mt-5 rounded-xl border border-[var(--accent-strong)]/35 bg-[var(--accent-soft)] p-5">
        <h3 className="mb-2 text-sm font-semibold text-[var(--ink)]">Assumptions</h3>
        <ul className="list-disc space-y-1 pl-5 text-sm text-[var(--ink)]">
          {result.assumptions.map((a, i) => (
            <li key={i}>{a}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}
