import os
import time
from The6ix.settings import REDIS_LOCK_KEY, REDIS_INSTANCE
from The6ix.celery import app


@app.task(name='clashstats.tasks.scoring')
def simulation(years, clients, companies, deciles):
    start_year = 2021

    sim_params = {
        'clients': clients,
        'companies': companies,
        'recog_base': True,
        'recog_prop': 0.0,
        'year': start_year,
        'end_year': (start_year + years),
        'freq': risk_vars['freq'],
        'severity': risk_vars['severity'],
        'risk_slope': risk_vars['risk_slope'],
        'deciles': deciles,
        'target_marketing': False,
        'target_limit': 0.50,
        'shop_base': 0.32,
        'shop_slpe': -8.0,
        'shop_sens': 2.0,
        'shop_skew': 0.3,
        'max_mktg_exp': 0.05,
        'init_mktg_exp': 0.025,
        'lottery_mult': 1.0,
        'lottery_prem_wt': 0.01,
        'price_srvc': 0.40,
        'price_sens': 0.40,
        'fixed_exp': exp_vars['fixed_exp'],
        'expos_var_exp': exp_vars['expos_var_exp'],
        'prem_var_exp': exp_vars['prem_var_exp'],
        'marketing_exp': exp_vars['marketing_exp'],
        'prem_var_prft': exp_vars['prem_var_prft'],
    }

    my_save_path = os.getcwd() + '/src_code/application/pickles/'
    my_rept_path = os.getcwd() + '/src_code/application/results/'

    print(clients, deciles)

    timeout = (60 * 10)
    have_lock = False
    my_lock = REDIS_INSTANCE.lock(REDIS_LOCK_KEY, timeout=timeout)
    while have_lock == False:
        have_lock = my_lock.acquire(blocking=False)
        if have_lock:
            print('unique process commencing...')
            from .Tasks_Scoring.score import Score

            Client.reset_client_no()
            Company.reset_company_id()
            s = Sim(**sim_params)
            market_by_year = s.control_flow(my_save_path)
            report = final_report(market_by_year, my_rept_path)
            del s, Sim
        else:
            print('waiting for lock to commence...')
            time.sleep(10)
    my_lock.release()
    return report