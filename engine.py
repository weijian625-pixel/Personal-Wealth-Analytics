import json
from datetime import datetime
import yfinance as yf

class AssetEngine:
    def __init__(self, json_path="portfolio.json"):
        self.json_path = json_path
        self.data = self.load_data()
        self.usd_to_myr = 4.70

    def load_data(self):
        with open(self.json_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_data(self):
        with open(self.json_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
        print("💾 Asset data successfully saved to local storage!")

    def update_asset(self, name, **kwargs):
        if name in self.data["assets"]:
            for key, value in kwargs.items():
                if key in self.data["assets"][name]:
                    self.data["assets"][name][key] = value
            self.save_data()

    def update_rates_and_prices(self):
        try:
            exchange_rate = yf.Ticker("USDMYR=X").history(period="1d")
            if not exchange_rate.empty:
                self.usd_to_myr = exchange_rate['Close'].iloc[-1]
            tickers = yf.Tickers("VOO GLDM 1155.KL")
            self.voo_price = tickers.tickers['VOO'].history(period="1d")['Close'].iloc[-1]
            self.gldm_price = tickers.tickers['GLDM'].history(period="1d")['Close'].iloc[-1]
            self.maybank_price = tickers.tickers['1155.KL'].history(period="1d")['Close'].iloc[-1]
        except Exception as e:
            print(f"Fallback mechanism triggered for market rates: {e}")
            self.voo_price = 500.0
            self.gldm_price = 45.0
            self.maybank_price = 10.40

    def calculate_mmf(self, asset_info):
        principal = asset_info["principal"]
        rate = asset_info["rate"]
        start_date = datetime.strptime(asset_info["start_date"], "%Y-%m-%d")
        days_passed = (datetime.now() - start_date).days
        return principal + (principal * (rate / 365) * max(0, days_passed))

    def calculate_portfolio(self):
        self.update_rates_and_prices()
        assets = self.data["assets"]
        report = {}
        total_wealth_myr = 0.0

        for name, info in assets.items():
            if info["type"] == "us_stock":
                current_price_usd = self.voo_price if name == "VOO" else self.gldm_price
                current_value_myr = info["shares"] * current_price_usd * self.usd_to_myr
            elif info["type"] == "bursa_stock":
                # 🚨 Core Logic: Total value of Maybank = Stock Equity Value + Cash Pool Reservoir
                stock_value = info["shares"] * self.maybank_price
                cash_pool = info.get("cash_pool", 0.0)
                current_value_myr = stock_value + cash_pool
            elif info["type"] == "fixed_yield":
                current_value_myr = self.calculate_mmf(info)
            elif info["type"] == "epf_account":
                current_value_myr = info["balance"]

            report[name] = round(current_value_myr, 2)
            total_wealth_myr += current_value_myr

        report["TOTAL_WEALTH"] = round(total_wealth_myr, 2)
        return report

    def calculate_rebalancing(self, current_balances, cash_inflow=0.0):
        total_wealth = current_balances["TOTAL_WEALTH"]
        post_total_wealth = total_wealth + cash_inflow
        if post_total_wealth == 0: return {}

        target_value_per_asset = post_total_wealth * 0.20
        rebalance_report = {}
        raw_diffs = {}
        total_positive_diff = 0.0

        for name, current_value in current_balances.items():
            if name == "TOTAL_WEALTH": continue
            diff = target_value_per_asset - current_value
            raw_diffs[name] = diff
            if diff > 0: total_positive_diff += diff

        for name, current_value in current_balances.items():
            if name == "TOTAL_WEALTH": continue
            actual_pct = (current_value / total_wealth) * 100 if total_wealth > 0 else 0
            
            allocated_cash = 0.0
            if cash_inflow > 0:
                if total_positive_diff > 0 and raw_diffs[name] > 0:
                    allocated_cash = cash_inflow * (raw_diffs[name] / total_positive_diff)
            else:
                allocated_cash = target_value_per_asset - current_value

            rebalance_report[name] = {
                "actual_pct": actual_pct,
                "target_pct": 20.0,
                "suggested_investment": round(allocated_cash, 2)
            }
        return rebalance_report

    def execute_investment_plan(self, plan_report):
        """
        🚨 Execution Engine: Persists and commits capital allocation changes into the local database upon confirmation.
        """
        assets = self.data["assets"]
        for name, info in plan_report.items():
            cash = info["suggested_investment"]
            if cash <= 0: continue
            
            if name == "VOO" or name == "GLDM":
                # Convert MYR cash inflow into fractional US shares based on real-time price and Forex rate
                price_usd = self.voo_price if name == "VOO" else self.gldm_price
                cash_usd = cash / self.usd_to_myr
                added_shares = cash_usd / price_usd
                assets[name]["shares"] += added_shares
            elif name == "Maybank":
                # For Bursa stock, instead of direct fractional share adjustment, route capital into the cash_pool reservoir
                assets[name]["cash_pool"] = assets[name].get("cash_pool", 0.0) + cash
            elif name == "MMF":
                # Compounds existing principal for Money Market Funds and resets the accrual timeline
                new_principal = self.calculate_mmf(assets["MMF"]) + cash
                assets["MMF"]["principal"] = new_principal
                assets["MMF"]["start_date"] = datetime.now().strftime("%Y-%m-%d")
            elif name == "EPF":
                assets["EPF"]["balance"] += cash
        
        self.save_data()

    def convert_maybank_pool_to_shares(self):
        """
        🚨 Order Matching Logic: Converts accumulated reservoir cash into actual equity holdings once the balance satisfies board lot requirements (1 lot = 100 shares).
        """
        assets = self.data["assets"]
        cash_pool = assets["Maybank"].get("cash_pool", 0.0)
        one_lot_cost = 100 * self.maybank_price
        
        if cash_pool >= one_lot_cost:
            lots_to_buy = int(cash_pool // one_lot_cost)
            shares_to_add = lots_to_buy * 100
            actual_cost = shares_to_add * self.maybank_price
            
            # Deduct from cash pool reservoir and increment physical share count
            assets["Maybank"]["cash_pool"] -= actual_cost
            assets["Maybank"]["shares"] += shares_to_add
            self.save_data()
            return lots_to_buy
        return 0
