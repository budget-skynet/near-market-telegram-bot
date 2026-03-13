#!/usr/bin/env python3
"""
NEAR AI Marketplace Telegram Bot
Integrates with market.near.ai — browse jobs, check wallet, place bids
"""
import os
import json
import logging
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN  = os.environ["BOT_TOKEN"]
AM_API_KEY = os.environ.get("AM_API_KEY", "")
BASE_URL   = "https://market.near.ai/v1"


def am_headers() -> dict:
    return {"Authorization": f"Bearer {AM_API_KEY}", "Content-Type": "application/json"}


async def fetch_json(session: aiohttp.ClientSession, method: str, path: str, **kwargs):
    url = BASE_URL + path
    async with session.request(method, url, headers=am_headers(), **kwargs) as r:
        r.raise_for_status()
        return await r.json()


# ── /start ──────────────────────────────────────────────────────────────────

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("📋 Open Jobs",    callback_data="jobs_open")],
        [InlineKeyboardButton("💼 My Bids",       callback_data="my_bids")],
        [InlineKeyboardButton("💰 Wallet",        callback_data="wallet")],
        [InlineKeyboardButton("🛠 Services",      callback_data="services")],
    ]
    await update.message.reply_text(
        "🤖 *NEAR AI Marketplace Bot*\n\n"
        "Browse jobs, check your wallet, and manage bids on market.near.ai",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )


# ── /jobs ───────────────────────────────────────────────────────────────────

async def cmd_jobs(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await _send_jobs(update, ctx, status="open")


async def _send_jobs(update: Update, ctx: ContextTypes.DEFAULT_TYPE, status="open", offset=0):
    msg = update.message or update.callback_query.message
    async with aiohttp.ClientSession() as s:
        try:
            data = await fetch_json(s, "GET", f"/jobs?status={status}&limit=5&offset={offset}")
            jobs = data if isinstance(data, list) else data.get("data", [])
        except Exception as e:
            await msg.reply_text(f"❌ Error fetching jobs: {e}")
            return

    if not jobs:
        await msg.reply_text("No jobs found.")
        return

    lines = [f"*{status.upper()} JOBS* (showing {offset+1}–{offset+len(jobs)})\n"]
    kb = []
    for j in jobs:
        jid  = j.get("job_id", "?")
        title = j.get("title", "?")[:45]
        budget = j.get("budget_max", "?")
        lines.append(f"• `{jid[:8]}` {budget}N — {title}")
        kb.append([InlineKeyboardButton(f"🔍 {title[:30]}", callback_data=f"job_{jid}")])

    if len(jobs) == 5:
        kb.append([InlineKeyboardButton("➡️ Next page", callback_data=f"jobs_page_{offset+5}")])
    kb.append([InlineKeyboardButton("🏠 Menu", callback_data="menu")])

    await msg.reply_text(
        "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )


# ── /wallet ──────────────────────────────────────────────────────────────────

async def cmd_wallet(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.callback_query.message
    async with aiohttp.ClientSession() as s:
        try:
            data = await fetch_json(s, "GET", "/wallet/balance")
        except Exception as e:
            await msg.reply_text(f"❌ Error: {e}")
            return
    balance = data.get("balance") or data.get("available") or str(data)
    await msg.reply_text(f"💰 *Wallet Balance*\n\n`{balance} NEAR`", parse_mode="Markdown")


# ── /bids ────────────────────────────────────────────────────────────────────

async def cmd_bids(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.callback_query.message
    async with aiohttp.ClientSession() as s:
        try:
            data = await fetch_json(s, "GET", "/agents/me/bids?limit=10")
            bids = data if isinstance(data, list) else data.get("bids", [])
        except Exception as e:
            await msg.reply_text(f"❌ Error: {e}")
            return

    if not bids:
        await msg.reply_text("No bids found.")
        return

    lines = ["*MY BIDS*\n"]
    for b in bids:
        status = b.get("status", "?")
        amount = b.get("amount", "?")
        job_id = str(b.get("job_id", "?"))[:8]
        emoji = {"pending": "⏳", "accepted": "✅", "rejected": "❌", "withdrawn": "🔙"}.get(status, "❓")
        lines.append(f"{emoji} `{job_id}` — {amount}N — {status}")

    await msg.reply_text("\n".join(lines), parse_mode="Markdown")


# ── /services ────────────────────────────────────────────────────────────────

async def cmd_services(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.callback_query.message
    async with aiohttp.ClientSession() as s:
        try:
            data = await fetch_json(s, "GET", "/services?limit=8")
            svcs = data if isinstance(data, list) else data.get("data", [])
        except Exception as e:
            await msg.reply_text(f"❌ Error: {e}")
            return

    if not svcs:
        await msg.reply_text("No services found.")
        return

    lines = ["*AVAILABLE SERVICES*\n"]
    for s in svcs:
        name  = s.get("name", "?")[:40]
        price = s.get("price_amount", "?")
        cat   = s.get("category", "")
        lines.append(f"• {name} — {price}N {f'({cat})' if cat else ''}")

    await msg.reply_text("\n".join(lines), parse_mode="Markdown")


# ── Job detail ───────────────────────────────────────────────────────────────

async def show_job_detail(update: Update, ctx: ContextTypes.DEFAULT_TYPE, job_id: str):
    query = update.callback_query
    async with aiohttp.ClientSession() as s:
        try:
            j = await fetch_json(s, "GET", f"/jobs/{job_id}")
        except Exception as e:
            await query.message.reply_text(f"❌ Error: {e}")
            return

    title  = j.get("title", "?")
    status = j.get("status", "?")
    budget = j.get("budget_max", "?")
    tags   = ", ".join(j.get("tags", []))
    desc   = j.get("description", "")[:300]

    text = (
        f"📋 *{title}*\n\n"
        f"Status: {status}\nBudget: {budget} NEAR\nTags: {tags}\n\n"
        f"{desc}"
    )
    kb = [[
        InlineKeyboardButton("💼 Place Bid", callback_data=f"bid_{job_id}_{budget}"),
        InlineKeyboardButton("🔗 Open", url=f"https://market.near.ai/jobs/{job_id}")
    ], [InlineKeyboardButton("◀️ Back", callback_data="jobs_open")]]

    await query.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))


# ── Callback router ──────────────────────────────────────────────────────────

async def button_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "menu":
        await start(update, ctx)
    elif data == "jobs_open":
        await _send_jobs(update, ctx, status="open")
    elif data.startswith("jobs_page_"):
        offset = int(data.split("_")[-1])
        await _send_jobs(update, ctx, status="open", offset=offset)
    elif data == "my_bids":
        await cmd_bids(update, ctx)
    elif data == "wallet":
        await cmd_wallet(update, ctx)
    elif data == "services":
        await cmd_services(update, ctx)
    elif data.startswith("job_"):
        job_id = data[4:]
        await show_job_detail(update, ctx, job_id)
    elif data.startswith("bid_"):
        parts  = data.split("_", 2)
        job_id = parts[1]
        budget = parts[2] if len(parts) > 2 else "?"
        ctx.user_data["pending_bid_job"] = job_id
        await query.message.reply_text(
            f"💼 *Place a bid on job* `{job_id[:8]}`\n\n"
            f"Budget: {budget} NEAR\n\n"
            f"Reply with your bid amount (e.g. `4.5`):",
            parse_mode="Markdown"
        )


# ── Text input for bid amount ─────────────────────────────────────────────────

async def text_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    job_id = ctx.user_data.get("pending_bid_job")
    if not job_id:
        await update.message.reply_text("Use /jobs to browse available work.")
        return

    try:
        amount = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Please send a valid number, e.g. `4.5`", parse_mode="Markdown")
        return

    async with aiohttp.ClientSession() as s:
        try:
            result = await fetch_json(s, "POST", f"/jobs/{job_id}/bids", json={
                "amount": str(amount),
                "proposal": "Autonomous AI agent ready to deliver. Fast, reliable, high quality."
            })
        except Exception as e:
            await update.message.reply_text(f"❌ Bid failed: {e}")
            return

    ctx.user_data.pop("pending_bid_job", None)
    bid_id = result.get("bid_id", "?")
    await update.message.reply_text(
        f"✅ *Bid placed!*\n\nBid ID: `{bid_id}`\nAmount: {amount} NEAR",
        parse_mode="Markdown"
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",    start))
    app.add_handler(CommandHandler("jobs",     cmd_jobs))
    app.add_handler(CommandHandler("wallet",   cmd_wallet))
    app.add_handler(CommandHandler("bids",     cmd_bids))
    app.add_handler(CommandHandler("services", cmd_services))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    logger.info("Bot started")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
