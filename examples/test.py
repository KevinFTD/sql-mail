#!/usr/bin/python
# coding:utf-8
__author__ = 'kevinftd'

from sqlmail.sqltable import SQLTable
from sqlmail.sqlchart import SQLLineChart
from sqlmail.email_util import NiceReportMail
import DataOp # personal module to get db connection

if __name__ == "__main__":
    db_conn = DataOp.GetDBConnect('mysql00')

    sql = u"""select
            date_format(stat_date, '%Y-%m-%d') `Date`,
            format(day_startup, 0) `Day run`,
            format(week_startup, 0) `Week run`,
            format(month_startup, 0) `Month run`
            from stat.kpi
            where version = 'total' and
            stat_date >= 20150520 and stat_date <= 20150526
            order by stat_date desc"""
    table = SQLTable(sql, db_conn=db_conn)

    sql = u"""select
            date_format(stat_date, '%Y-%m-%d') `Date`,
            version,
            day_startup `Day run`
            from stat.kpi
            where (version = 'total' or version = '7.3')
            and stat_date >= 20150520 and stat_date <= 20150526
            order by stat_date"""
    chart = SQLLineChart(sql, db_conn=db_conn, data_start_col=2)
    chart_file = chart.draw()

    email = NiceReportMail(me="kevin<kevin@qq.com>", recipients=["kevin@foxmail.com"], subject=u"Demo mail")
    email.set_template_content("test_template.html", {"table_run_state": table.to_html()})
    email.add_images({"chart_run_state": chart_file})
    email.send_mail(mail_server="smtp.qq.com", username="kevin@qq.com", password="qq_application_code")
