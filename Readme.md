sql-mail
==============

sql-mail is designed to send data report mail that almost every company or groups needs. It retrive data by sql and automatically converts results into HTML or chart file that can be put inot email. It also provides a simple wrapper of smtplib.SMTP for mail sending.

Requirements：
- Python >= 2.7
- Marksafe >= 0.23
- Jinja2 >= 2.7 


0. check a complete example in ./examples/test.py

1. send email with simple text context

    use **Email** class to send email directly
    ```python
    from sqlmail.email_util import EMail
    mail = Email(me="me", recipients=["xiaoA@qq.com", "xiaoB@qq.com"], 
                        subject="This is mail suject", content="Welcome to sqlmail")
    
    mail.send_mail(mail_server="smtp.qq.com")
    ```

2. Add simple table

    use **SQLTable** class to generate HTML table and put it into mail
    ```python
    from sqlmail.sqltable import SQLTable
    from sqlmail.email_util import EMail

    sql = "select date_format(stat_date, '%Y-%m-%d') `Date`, format(day_startup, 0) `Day run`, \
                format(week_startup, 0) `Week run`, format(month_startup, 0) `Month run` from stat.kpi \
                where version = 'total' and stat_date >= 20150520 and stat_date <= 20150526"
    table = SQLTable(sql, db_info=db_info)
    
    email = Email(me='me', recipients=["xiaoA@qq.com"], 
                        subject="This is mail subject", content=table.to_html())
    email.send_mail(mail_server="smtp.qq.com")
    ```

    When using **SQLTable** class，all data format should be done by SQL，for example, use   `date_format` to format DATETIME type and use `format` to format INTEGER or FLOAT

3. Make tables look pretty

    Use **NiceReportMail** instead of using Email class. This class contains a CSS style which makes table look pretty. Also you can use **set_style_template** method for your own CSS.

    ```python
    from sqlmail.sqltable import SQLTable
    from sqlmail.email_util import NiceReportMail

    email = NiceReportMail(me='me', recipients=["xiaoA@qq.com"], 
                        subject="This is mail subject", content=table.to_html())
    email.send_mail(mail_server="smtp.qq.com")
    ```

4. Template to organise mail structure

    When you need multiple tables and text in one mail, you need use template to organise them. A template is an HTML file that is the same in Jinja2. **set_template_content** method can be used to set a template file and value to fill in the template.
    ```python
    from sqlmail.email_util import NiceReportMail
    
    email = NiceReportMail('me', ["xiaoA@qq.com"], u"This is mail subject")
    # should use absolute path for the template file 
    email.set_template_content("%s/test_template.html" % (os.path.dirname(os.path.abspath(__file__)),), 
                                        {"tag1": "content under tag1", "tag2": "content under tag2"}
                                        )
    email.send_mail(mail_server="smtp.qq.com")
    ```

    test_template.html:
    ```html
    <h1>1. Overview</h1>
    {{tag1}}
    <h1>2. Trend pic</h1>
    {{tag2}}
    ```
    And the {{tag1}}、{{tag2}} will be replaced by value of the second parameter in `set_template_content`

5. Add a simple line chart into mail
    
    ```python
    from sqlmail.email_util import NiceReportMail
    from sqlmail.sqlchart import SQLLineChart
    
    sql = "select date_format(stat_date, '%Y-%m-%d') `Date`, format(day_startup, 0) `Day run`, format(week_startup, 0) `Week run`, \
            format(month_startup, 0) `Month run` from stat.kpi \
            where version = 'total' and stat_date >= 20150520 and stat_date <= 20150526 order by stat_date desc"
    table = SQLTable(sql, db_conn=db_conn)  # a table
    
    sql = "select stat_date `Date`, day_startup `Day run`, week_startup `Week run` from stat.kpi \
        where version = 'total' and stat_date >= 20150520 and stat_date <= 20150526 \
        order by stat_date"
    chart = SQLLineChart(sql, db_conn=db_conn, data_start_col=2)
    chart_file = chart.draw()  # a line chart
    
    email = NiceReportMail('me', ["xiaoA@qq.com"], u"mail suject")
    # should use absolute path for template file
    email.set_template_content("%s/test_template.html" % (os.path.dirname(os.path.abspath(__file__)),),           
                                        {"table_run_state": table.to_html()}
                                        )
    email.add_images({"chart_run_state": chart_file})  # add images file
    email.send_mail(mail_server="smtp.qq.com")
    ```

    test_template.html is in the same directory and "chart_run_state" is used to mark the place to put the image.
    ```html
    <h1>1. Overview</h1>
    {{table_run_state}}
    <h1>2. Trend pic</h1>
    <img src="cid:chart_run_state">
    ```

6. Divide one column into multiple lines

    In the last part, a line chart is drawn from a SQL where the FIRST column is x-Axis and each of the rest column is value for the Y-axis. That is each of the rest column is a line in the chart. But sometimes, it is necessary to divide a column data into multiple part, each part for a single line. For example, there is a database table that contains information for different version and it is requested to draw lines for each version. A SQL might be like:

    ```sql
    SELECT stat_date, version, value from t1 where ....
    ```
    And with parameter data_start_col when init SQLLineChart, the class will know the real line value is start from column-data_start_col.

    ```python
    from sqlmail.email_util import NiceReportMail
    from sqlmail.sqlchart import SQLLineChart

    sql = "select stat_date `Date`, version `Version`, day_startup `Day run` from stat.kpi \
            where (version = 'total' or version = '7.3.503.1459') and stat_date >= 20150520 and stat_date <= 20150526 \
            order by stat_date"
    chart = SQLLineChart(sql, db_conn=db_conn, data_start_col=2) # divide one column into multiple lines with [1, data_start_col) column value
    chart.set_line_label_order([u"7.3.503.1459-Day run", u"total-Day run"]) # user-defined label order
    chart_file = chart.draw()
    
    email = NiceReportMail('me', ["xiaoA@qq.com"], u"One column into multiple lines", )
    # should use absolute path for template file
    email.set_template_content("%s/test_template.html" % (os.path.dirname(os.path.abspath(__file__)),), 
                                        {"table_run_state": table.to_html()}
                                        )
    email.add_images({"chart_run_state": chart_file})
    email.send_mail(mail_server="smtp.qq.com")
    ```

7. 数据源不在同一个host

    显然，如果数据不在同一个主机上，就不能再使用一个sql取到全部数据，这时可以使用MultiSQLTable类，进行多数据源数据的聚合。
    （1）首先构造一个MultiSQLTable对象，然后使用add_data_source方法添加多个数据源

    ```python
    from Mail.email_proxy import NiceReportMail
    from Mail.Table import MultiSQLTable

    sql1 = "select date_format(stat_date, '%Y-%m-%d') 日期, day_startup 日启动 \
            from stat.kpi \
            where version = 'total' and stat_date >= 20150520 and stat_date <= 20150526 order by stat_date desc"
    sql2 = "select date_format(stat_date, '%Y-%m-%d') 日期, \
            week_startup 周启动, format(month_startup, 0) 月启动 from stat.kpi \
            where version = 'total' and stat_date >= 20150520 and stat_date <= 20150526"
    
    table = MultiSQLTable()
    table.add_data_source(sql1, db_info=db_info1)
    table.add_data_source(sql2, db_info=db_info2)
    ```

    上述代码添加了两个数据源，它们将默认按照第一列的值将两个结果集做join，需要注意的是，如果这一列不是str类型，请在SQL中先将类型转换为str，不然或报错，例如上述sql使用date_format将date类型转为str。如果仅根据第一列不能满足需求，需要根据更多列做join时，使用MultiSQLTable(join_data_cols=number)方法，数据将按照前number列做join操作。

    （2）设置表格展示哪些列，列名与sql中的别名对应，因此不允许多个数据源的sql存在相同的别名。

    ```python
    table.set_table_cols([u'日期', u'日启动', u'周启动', u'总启动'])  # 注意中文使用Unicode
    ```
    （3）如果取出的值没有进行格式化，可以使用set_col_format方法设置样式，比如千分符。
    ```python
    table.set_col_format(u'日启动', lambda x: format(float(x)/100,','))
    ```
    
    （4）取出的数据中并没有"总启动"这一列，需要增加这一列数据的定义
    ```python
    table.set_col_definition(u'总启动', lambda row: row[u'日启动'] + row[u'周启动'])  # 注意中文使用Unicode
    ```