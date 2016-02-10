#!/usr/bin/python
# coding:utf-8
__author__ = 'kevinftd'


import MySQLdb
import json
import os
import platform
import hashlib
import datetime


class ChartInitException(Exception):
    """Exception when init chart using SQL """


class NotEnoughColumnsException(Exception):
    """Exception when there are not enough columns for chart """


class Chart(object):
    """
    Base class. Use SQLLineChart or SQLStackChart instead of this class.

    Generate chart files with highcharts.js and phantomjs engine
    """
    def __init__(self, sql, title):

        self.sql = sql
        self.options = {
            "chart": {'width': 800},
            "title": {"text": title},
            "xAxis": {},
            "yAxis": {'title': {'text': ''}},
            'plotOptions': {},
            "series": []
        }

    def __draw__(self):

        common_prefix = '%s/%d_%s' % (os.getcwd(), os.getpid(), hashlib.md5(self.sql).hexdigest())

        infile_name = '%s.json' % (common_prefix,)
        outfile_name = '%s.jpg' % (common_prefix,)

        infile = open(infile_name, 'w')
        infile.write(json.JSONEncoder().encode(self.options))
        infile.close()

        base_path = os.path.dirname(os.path.abspath(__file__))
        if platform.system() == "Linux":
            exec_file = "phantomjs"
        else:
            exec_file = "phantomjs.exe"
        command = "{base}/bin/phantomjs/bin/{phantomjs} \
                    {base}/bin/phantomjs/highcharts-convert.js \
                    -infile {infile} -outfile {outfile} -scale 2.5 -width 800".format(base=base_path,
                                                                                      phantomjs=exec_file,
                                                                                      infile=infile_name,
                                                                                      outfile=outfile_name)
        os.system(command)
        os.remove(infile_name)

        return outfile_name

    def draw(self):
        raise NotImplementedError()

class SQLLineChart(Chart):
    """
    line chart with data from SQL

    Usually, the FIRST column is x-axis value such as date time.
    Each of the rest column will be a line in the chart.

    But it also support divide data in one column into many lines.
    Example:
    >>>>query_sql = "select insert_time, product_type, value from T1"
    >>>>chart = SQLLineChart(query_sql, db_conn=db_conn, data_start_col=2)

    Note that data_start_col is 2.
    The result is a chart where there is one line for each product type.
    And if there's multiple product type, there will be multiple lines in the chart.
    """
    def __init__(self, sql, db_info=None, db_conn=None, title=None,
                 data_start_col=1, line_label_order=None, data_label=False):
        """
        :param db_info: MySQLdb.connect(**server_info)
        :param db_conn: MySQLdb.connect
        :param title: chart title
        :param data_start_col: the real data starts from data_start_col
        :param line_label_order: line labels shows in order according to this list
        :param data_label: if show each data value besides the line
        :return:
        """
        Chart.__init__(self, sql, title)
        self.options['chart']['type'] = "line"
        self.options["xAxis"]["type"] = "category"
        self.options['plotOptions']['line'] = {'marker': {'enabled': False}}    # if show each data point
        if data_label:
            self.options['plotOptions']['line'] = {'marker': {'enabled': True}}
            self.options['plotOptions']['series'] = {'dataLabels': {'enabled': True}}  # if show each data value

        try:
            if not db_conn:
                db_conn = MySQLdb.connect(**db_info)
            db_cursor = db_conn.cursor()
            db_cursor.execute(sql)
            db_conn.commit()

            self.data = db_cursor.fetchall()
            self.theader_list = [column[0] for column in db_cursor.description]
            self.col_description = db_cursor.description
            self.data_start_col = data_start_col if data_start_col >=1 else 1
            self.line_label_order = line_label_order
        except Exception as e:
            raise ChartInitException(e.message)


    def set_line_label_order(self, value):
        if isinstance(value, list):
            self.line_label_order = value

    def draw(self):
        if len(self.theader_list) <= 1:
            raise NotEnoughColumnsException("Num of cols "
                                            "fetched by sql is less than 1. "
                                            "Cannot draw chart")

        """
        In highcharts, xAxis has four optional types
        linear, logarithmic, datetime and category

        Here we only use category
        and if it is date type, it should be converted into str manually

        Ref: http://api.highcharts.com/highcharts#xAxis.type
        """

        if self.data_start_col == 1: # line data starts from column-1, column-0 is x-axis data such as datetime

            """
            draw a line for each column， so extract value from self.data by columns
            """
            # y-axis values
            for i in range(self.data_start_col, len(self.theader_list)):
                name = self.theader_list[i]
                values = [r[i] for r in self.data]
                self.options["series"].append({"name": name, "data": values})

            # x-axis values
            self.options["xAxis"]["categories"] = \
                [r[0].strftime("%m-%d") if isinstance(r[0], datetime.date) else r[0]
                 for r in self.data]
        else:
            # column-0 is x-axis data such as datetime，
            # column-1~column-data_start_col is group info that
            # divides one column into multiple lines
            """
            extract value from self.data by columns
            """
            names = set()
            values = dict()
            for i in range(self.data_start_col, len(self.theader_list)):
                for r in self.data:
                    name = self._generate_series_name(r, i) # line name is composed by group info and column name
                    names.add(name)
                    if name not in values:
                        values[name] = list()
                    values[name].append(r[i])

            if not self.line_label_order:
                show_line_names = names
            else:
                show_line_names = self.line_label_order

            # y-axis
            for name in show_line_names:
                self.options["series"].append({"name": name, "data": values.get(name, list())})

            # x-axis
            self.options["xAxis"]["categories"] = list()
            category_set = set()
            for r in self.data:
                if r[0] not in category_set:
                    category_set.add(r[0])
                    self.options["xAxis"]["categories"].append(r[0].strftime("%m-%d") if isinstance(r[0], datetime.date) else r[0])

        return self.__draw__()

    def _generate_series_name(self, row, current_col_index):
        """ line name is composed by
        column-1~column-data_start_col value and current column name
        """
        name = " ".join([row[col] for col in range(1, self.data_start_col)])

        if len(self.theader_list)-self.data_start_col >= 2:
            # if there is many data columns, append current data column name
            name = u"%s-%s" % (name, self.theader_list[current_col_index].decode("utf-8"))

        return name

class SQLStackChart(Chart):
    """
    stack chart with data from SQL
    """
    def __init__(self, sql, db_info=None, db_conn=None, title=None):
        """
        :param db_info: MySQLdb.connect(**server_info)
        :param db_conn: MySQLdb.connect
        :param title: chart title
        :return:
        """
        Chart.__init__(self, sql, title)
        self.options['chart']['type'] = "column"
        self.options['plotOptions'] = {'column':{'stacking': 'percent','dataLabels':{'enabled':True, 'color':'#000000', 'format': '{percentage:.2f}%'}}}
        self.options['xAxis'] = {}

        # prefer to use following colors first
        self.default_colors = ['#4472A5', '#A94642', '#87A34E', '#70588D', '#4097AD', '#D9833C']
        try:
            if not db_conn:
                db_conn = MySQLdb.connect(**db_info)
            db_cursor = db_conn.cursor()
            db_cursor.execute(sql)
            db_conn.commit()

            self.data = db_cursor.fetchall()
            self.theader_list = [column[0] for column in db_cursor.description]
            self.col_description = db_cursor.description

            self.options['xAxis']['categories'] = [r[0] for r in self.data]
        except Exception as e:
            raise ChartInitException(e.message)

    def draw(self):
        for i in range(1, len(self.theader_list)):
            values = list()
            for r in self.data:
                values.append(r[i])
            item = {"name": self.theader_list[i], "data": values}
            if i <= len(self.default_colors):
                item["color"] = self.default_colors[i-1]
            self.options["series"].append(item)

        return self.__draw__()


if __name__ == "__main__":
    import DataOp
    sql = """
                    select
                    date_format(stat_date, '%m-%d'),
                    supply_name,
                    day_run
                    from db_134.supply_kpi_fenlei_otin
                    where stat_date >= {start_date} and stat_date <= {end_date}
                    and ((sid_level=2 and supply in ('内部', '其他')))
                    order by stat_date
    """.format(start_date = 20151225, end_date=20160102)
    chart = SQLLineChart(sql, db_conn=DataOp.GetDBConnect("result"), data_start_col=2, data_label=True)
    dau_chart_file = chart.draw()