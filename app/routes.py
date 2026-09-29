from datetime import date, datetime
from flask import Blueprint, flash, redirect, render_template, request, url_for
from sqlalchemy import func
from app import db
from app.models import Expense

main = Blueprint("main", __name__)

#Allowed expense categories (used by the form and the filter) -->
CATEGORIES = ["Food", "Transport", "Bills", "Shopping", "Health", "Entertainment", "Other"]


def read_form():
    """Validate the form and return (data, error)."""
    title = request.form.get("title", "").strip()
    category = request.form.get("category", "")
    try:
        amount = float(request.form.get("amount", ""))
        when = datetime.strptime(request.form.get("date", ""), "%Y-%m-%d").date()
    except ValueError:
        return None, "Enter a valid amount and date."
    if not title:
        return None, "Enter a title."
    if amount <= 0:
        return None, "Amount must be greater than zero."
    if category not in CATEGORIES:
        return None, "Choose a category."
    return {"title": title, "amount": amount, "category": category, "date": when}, None


@main.route("/")
def home():
    # Filter by category if one is chosen in the URL -->
    selected = request.args.get("category", "")
    query = Expense.query
    if selected in CATEGORIES:
        query = query.filter_by(category=selected)
    expenses = query.order_by(Expense.date.desc(), Expense.id.desc()).all()

    total = sum(e.amount for e in expenses)

    today = date.today()
    # Total spent since the 1st of this month.
    month_total = (
        db.session.query(func.coalesce(func.sum(Expense.amount), 0))
        .filter(Expense.date >= today.replace(day=1))
        .scalar()
    )

    # Group and sum expenses per category for the summmary list -->
    by_category = (
        db.session.query(Expense.category, func.sum(Expense.amount))
        .group_by(Expense.category)
        .order_by(func.sum(Expense.amount).desc())
        .all()
    )

    return render_template(
        "home.html",
        expenses=expenses,
        total=total,
        month_total=month_total,
        by_category=by_category,
        categories=CATEGORIES,
        selected=selected,
    )


@main.route("/add", methods=["GET", "POST"])
def add_expense():
    if request.method == "POST":
        data, error = read_form()
        if error:
            flash(error)
        else:
            db.session.add(Expense(**data))
            db.session.commit()
            flash("Expense added.")
            return redirect(url_for("main.home"))

    return render_template(
        "add_expense.html", expense=None, categories=CATEGORIES, today=date.today()
    )


@main.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_expense(id):
    expense = db.get_or_404(Expense, id)

    if request.method == "POST":
        data, error = read_form()
        if error:
            flash(error)
        else:
            for key, value in data.items():
                setattr(expense, key, value)
            db.session.commit()
            flash("Changes saved.")
            return redirect(url_for("main.home"))

    return render_template(
        "add_expense.html", expense=expense, categories=CATEGORIES, today=date.today()
    )


@main.route("/delete/<int:id>", methods=["POST"])
def delete_expense(id):
    expense = db.get_or_404(Expense, id)
    db.session.delete(expense)
    db.session.commit()
    flash("Expense deleted.")
    return redirect(url_for("main.home"))
