const money = value => `PKR ${value.toLocaleString("en-PK", { maximumFractionDigits: 2 })}`;
const names = ["Food", "Groceries", "Transport", "Shopping", "Bills", "Health", "Education", "Entertainment", "Other"];

export function replyToSpending(question, transactions, allowance, connected, previous = "", now = new Date()) {
  const q = question.toLowerCase();
  if (/^(hi|hello|hey)[!. ]*$/.test(q)) return "Hi! Ask me about your spending, a category, your balance, a budget, or your next allowance. I calculate answers from your saved records.";
  if (/help|what can you|how.*work/.test(q)) return "Try: How much did I spend this month? What about last month? How much on Food? Suggest a budget. When is my next allowance? I use your transaction records and allowance settings; I don’t move money or predict future expenses.";
  if (/allowance|payday|payment date/.test(q)) {
    if (!allowance?.amount || !allowance?.nextDate) return "Set your monthly allowance and next allowance date in Settings first.";
    return `Your planned monthly allowance is ${money(Number(allowance.amount))}. Your next allowance date is ${allowance.nextDate}. This is your saved plan, not confirmed income.`;
  }
  if (!connected) return "I can’t read your transactions while the server is unavailable. Please refresh Overview and try again. You can still ask about your saved allowance.";
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  let start = new Date(today.getFullYear(), today.getMonth(), 1);
  let end = new Date(today); end.setDate(end.getDate() + 1);
  let period = "this month";
  if (/last month/.test(q)) { end = new Date(start); start.setMonth(start.getMonth() - 1); period = "last month"; }
  else if (/today/.test(q)) { start = today; period = "today"; }
  else if (/week|7 days/.test(q)) { start = new Date(today); start.setDate(start.getDate() - 6); period = "the last 7 days"; }
  else if (/all time|overall/.test(q)) { start = new Date(0); period = "all recorded time"; }
  const rows = transactions.filter(row => {
    const date = new Date(`${row.date}T00:00:00`);
    return date >= start && date < end && Number.isFinite(Number(row.amount)) && Number(row.amount) > 0;
  });
  const expenses = rows.filter(row => row.kind === "Expense");
  const sum = list => list.reduce((total, row) => total + Number(row.amount), 0);
  const spent = sum(expenses), income = sum(rows.filter(row => row.kind === "Income"));
  if (/budget|afford|left.*allowance|remaining.*allowance/.test(q)) {
    if (!allowance?.amount) return "Add your monthly allowance in Settings so I can compare it with your spending and suggest a budget.";
    const monthSpent = sum(transactions.filter(row => row.kind === "Expense" && row.date?.slice(0,7) === `${today.getFullYear()}-${String(today.getMonth()+1).padStart(2,"0")}`));
    const remaining = Number(allowance.amount) - monthSpent;
    return `Your monthly allowance plan is ${money(Number(allowance.amount))}; recorded spending this month is ${money(monthSpent)}. ${remaining >= 0 ? `${money(remaining)} remains against that plan.` : `You are ${money(-remaining)} over that plan.`} A simple starting budget is 50% essentials (${money(Number(allowance.amount)*.5)}), 30% flexible spending (${money(Number(allowance.amount)*.3)}), and 20% savings (${money(Number(allowance.amount)*.2)}). Adjust these targets for your actual needs; allowance remaining is not your bank balance.`;
  }
  if (/upcoming|due|bill/.test(q)) return `You recorded ${money(sum(expenses.filter(row => row.category === "Bills")))} in Bills for ${period}. Upcoming bill due dates aren’t tracked yet, so I can’t confirm future bills.`;
  if (/balance|sav(e|ing)|income/.test(q)) return `For ${period}, recorded income is ${money(income)} and expenses are ${money(spent)}, leaving a recorded net of ${money(income-spent)}. This excludes any opening balance and unrecorded transactions; it isn’t a verified bank balance.`;
  const category = names.find(name => q.includes(name.toLowerCase()));
  if (category) return `You recorded ${money(sum(expenses.filter(row => row.category === category)))} in ${category} for ${period}.`;
  if (/spend|spent|expense|analy|category|most|last month|this month|today|week/.test(q) || /spend|expense/.test(previous.toLowerCase())) {
    if (!expenses.length) return `There are no recorded expenses for ${period}. Add expenses in Transactions or scan a receipt in Capture Studio.`;
    const totals = names.map(name => [name,sum(expenses.filter(row => row.category === name))]).filter(([,value]) => value > 0).sort((a,b) => b[1]-a[1]);
    return `You recorded ${money(spent)} across ${expenses.length} expenses for ${period}. Your largest category is ${totals[0]?.[0] || "Other"}. Breakdown: ${totals.map(([name,value]) => `${name}: ${money(value)}`).join("; ")}.`;
  }
  return "I can help with recorded spending, categories, income, balance, budgeting, bills, and allowance dates. Try ‘Analyze my spending’ or ‘When is my next allowance?’ This is a data-based assistant, not a general-purpose AI chat.";
}
