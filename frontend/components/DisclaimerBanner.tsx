/**
 * DisclaimerBanner — must be visible on every page, never conditional.
 * See CLAUDE.md and docs/decisions/003-tpb-compliance.md.
 */
export function DisclaimerBanner() {
  return (
    <div
      role="note"
      aria-label="Tax advice disclaimer"
      style={{
        background: "#fef9c3",
        border: "1px solid #eab308",
        borderRadius: 6,
        padding: "10px 16px",
        fontSize: 13,
        color: "#713f12",
        margin: "0 0 16px 0",
      }}
    >
      This tool helps organise tax information and prepare a review package.
      It does not provide final tax advice, does not lodge tax returns, and does not
      replace review by the user or a registered tax agent.
    </div>
  );
}
