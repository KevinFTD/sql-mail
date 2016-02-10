#!/usr/bin/python
# coding:utf-8
__author__ = 'kevinftd'

import MySQLdb
import os
import email_util


class Table(object):
    pass


class TableInitException(Exception):
    """Exception when init table using SQL """


class SQLTable(Table):
    """" generate HTML table with data retrieved by SQL

    each row in the SQL result will be one single row in the HTML table
    """
    def __init__(self, sql, db_info=None, db_conn=None, custom_order=None, custom_order_col=0):
        """
        :param sql: note to use `date_format` to format date type and use `format(int, n)` to format INTEGER or FLOAT
        :param db_info: MySQLdb.connect(**db_info)
        :param db_conn: MySQLdb.connect
        :param custom_order: To put the rows in some specific order,
                                provide a list that contains values in the FIRST column.
                                The rows will display in order according to this list.
        :param custom_order_col: default is 0 for the FIRST column, change it to order by other column
        :return:
        """
        try:
            if not db_conn:
                db_conn = MySQLdb.connect(**db_info)
            db_cursor = db_conn.cursor()
            db_cursor.execute(sql)
            db_conn.commit()

            self.data = db_cursor.fetchall()

            self.theader_list = [column[0].decode("utf-8") for column in db_cursor.description]

            if custom_order:
                order_data = list()
                for i in range(len(custom_order)):
                    for r in self.data:
                        if r[custom_order_col] == unicode(custom_order[i]):
                            order_data.append(r)
                            break
                self.data = order_data
        except Exception as e:
            raise TableInitException(e.message)

    def to_html(self):
        from jinja2 import Environment, FileSystemLoader
        env = Environment(loader=FileSystemLoader('%s/templates' % (os.path.dirname(os.path.abspath(__file__)),)))
        template = env.get_template('sql_table.html')
        html = template.render({"header": self.theader_list, "body": self.data})

        return html


class ColNameConflictException(Exception):
    """Exception that column name already exists """

class TableHeaderNullException(Exception):
    """Exception that table header should not be null """


class MultiSQLTable(Table):
    """
    Use this class when single SQL cannot meet your demand.

    Like JOIN in SQL, this class would join data from different SQL.
    For data retrieved by eachSQL, [0...sql_data_start) columns will be regarded as keyword to join.

    Example:
    SQL-1: select day, value1 from T1
    SQL-2: select day, value2 from T2

    Default sql_data_start is 1, so these two data set will be joined into:
    day, value1, value2
    xxx, xxxxxx, xxxxx
    zzz, zzzzzz, zzzzz
    """
    def __init__(self, table_headers, sql_data_start=1):

        if not table_headers:
            raise TableHeaderNullException("Table header is required as an argument.")

        self.data_cols_start = sql_data_start
        self.data_dict = dict()
        self.data_col_names = set()
        self.line_key_order = list()
        self.theader_list = table_headers
        self.format_functions = dict()

    def add_data_source(self, sql, db_info=None, db_conn=None):

        if not db_conn:
            db_conn = MySQLdb.connect(**db_info)
        db_cursor = db_conn.cursor(cursorclass=MySQLdb.cursors.DictCursor)
        db_cursor.execute(sql)
        db_conn.commit()

        results = db_cursor.fetchall()
        results_name = [column[0] for column in db_cursor.description]
        conflict_col_names = self.data_col_names & set(results_name[self.data_cols_start:])
        if len(conflict_col_names) > 0:
            raise ColNameConflictException("Conflict: %s already in data set" % (
                ",".join(list([n.decode("utf-8") for n in conflict_col_names]))))

        self.data_col_names.update(set(results_name[self.data_cols_start:]))
        if len(self.data_dict) == 0:
            first_data_source = True
        else:
            first_data_source = False

        for r in results:
            line_name = ",".join([r[results_name[i]] for i in range(self.data_cols_start)])
            if first_data_source:
                self.line_key_order.append(line_name)
            if line_name not in self.data_dict:
                self.data_dict[line_name] = dict()
            for col in results_name:
                self.data_dict[line_name][col.decode("utf-8")] = r[col]

    def add_complex_col(self, col_key, calculate_function):
        for line in self.data_dict:
            row = self.data_dict[line]
            row[col_key] = calculate_function(row)

    def set_col_format(self, col_key, format_function):
        self.format_functions[col_key] = format_function

    def _generate_rows(self):
        rows = list()
        for line_name in self.line_key_order:
            row_data = list()
            for col in self.theader_list:
                row_data.append(self.format_functions.get(col, lambda x: x)(self.data_dict[line_name].get(col, "")))
            rows.append(row_data)
        return rows

    def to_html(self):
        from jinja2 import Environment, FileSystemLoader
        env = Environment(loader=FileSystemLoader('%s/templates' % (os.path.dirname(os.path.abspath(__file__)),)))
        template = env.get_template('sql_table.html')
        html = template.render({"header": self.theader_list, "body": self._generate_rows()})

        return html


if __name__ == "__main__":
    db_info1 = {
        "host": "127.0.0.1",
        "user": "rd",
        "passwd": "rd",
        "port": 8989,
        "charset": "utf8"
        }

    db_info2 = {
        "host": "127.0.0.1",
        "user": "rd",
        "passwd": "rd",
        "port": 8901,
        "charset": "utf8"
        }
    """
    # ordinary table, single sql works.
    sql = "select date_format(stat_date, '%Y-%m-%d') `Date`, format(day_startup, 0) `Day run`, \
            format(week_startup, 0) `Week run`, format(month_startup, 0) `Month run` from stat_134.kpi \
            where version = 'total' and stat_date >= 20150520 and stat_date <= 20150526"
    table = SQLTable(sql, db_info=db_info)
    """

    # complex table, need join data from different DB host
    sql1 = "select\
            date_format(stat_date, '%Y-%m-%d') `Date`, day_startup `Day run` \
            from stat_134.kpi \
            where version = 'total' and stat_date >= 20150520 and stat_date <= 20150526 order by stat_date desc"
    sql2 = "select\
            date_format(stat_date, '%Y-%m-%d') `Date`, \
            week_startup `Week run`, format(month_startup, 0) `Month run` from stat_134.kpi \
            where version = 'total' and stat_date >= 20150520 and stat_date <= 20150526"

    table = MultiSQLTable([u'Date', u'Day run', u'Week run', u'Total run'])
    table.add_data_source(sql1, db_info=db_info1)
    table.add_data_source(sql2, db_info=db_info2)

    table.add_complex_col(u'Total run', lambda row: row[u'Day run'] + row[u'Week run'])
    table.set_col_format(u'Day run', lambda x: format(float(x)/100, ','))

    email_sender = email_util.NiceReportMail('sw_data', ["kevinftd@qq.com"], u"Table Test Mail", table.to_html())
    email_sender.send_mail("smtp.qq.com")
