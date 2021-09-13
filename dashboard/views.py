import math

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import View
from django.http import JsonResponse
from django.templatetags.static import static

from job.models import *
from ticketing.models import Ticket
from payment.models import PromotionPackage
from users.decorators import blocked_validation

acc_chart_cfg = {'credits': {'enabled': False},
                 'chart': {'type': 'area', 'marginRight': 0, 'spacingLeft': 0, 'spacingTop': 0, 'spacingBottom': 30},
                 'title': {'text': False}, 'subtitle': {'text': False, },
                 'xAxis': {'lineColor': '#EBEFF2',
                           'categories': [],
                           'labels': {'style': {'color': '#999999'}, 'y': 35},
                           'tickColor': '#EBEFF2',
                           'tickmarkPlacement': 'on'},
                 'yAxis': {'gridLineColor': '#EBEFF2', 'title': {'text': False},
                           'min': 0,
                           'max': 500,
                           'tickInterval': 50,
                           'labels': {'style': {'color': '#9BAFBB', 'fontSize': '12px'}},
                           'plotLines': [{'value': 0, 'width': 1, 'color': '#E7EBEE'}]},
                 'tooltip': {'backgroundColor': 'white', 'borderColor': None, 'borderWidth': None},
                 'legend': {
                     'layout': 'horizontal',
                     'align': 'left',
                     'verticalAlign': 'top',
                     'symbolHeight': 11,
                     'symbolWidth': 11,
                     'symbolPadding': 10,
                     'borderWidth': 0,
                     'y': -10,
                     'x': -15,
                     'padding': 15,
                     'itemDistance': 35,
                     'itemMarginTop': 10,
                     'itemMarginBottom': 5,
                     'itemStyle': {
                       'color': '#38596A',
                       'fontSize': 13,
                       'fontWeight': 'normal'
                     }},
                 'plotOptions': {'area': {'lineWidth': 0, 'marker': {'symbol': 'circle'}},
                                 'series': {'fillOpacity': 0.1,
                                            'stickyTracking': False,
                                            'states': {'hover': {'halo': {'size': 15}}}}
                                 }}


class DashboardView(View):
    template_name = 'dashboard/dashboard.html'

    @method_decorator(blocked_validation)
    @method_decorator(login_required(login_url='user_login'))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):

        latest_tickets = Ticket.objects.order_by('-date_modified').filter(user=request.user)
        deleted_status = JobStatus.objects.filter(name='deleted').first()
        latest_jobs = Job.objects.order_by('-date_modified').filter(user=request.user).exclude(status=deleted_status)
        payment_packages = PromotionPackage.objects.all()

        context = {'user': request.user,
                   'latest_tickets': latest_tickets,
                   'latest_jobs': latest_jobs,
                   'payment_packages': payment_packages}

        return render(self.request,
                      template_name=self.template_name,
                      context=context
                      )


def get_monthly_account_stats(temp_chart, request):
    month_list = ['January',
                  'February',
                  'March',
                  'April',
                  'May',
                  'June',
                  'July',
                  'August',
                  'September',
                  'October',
                  'November',
                  'December']
    frames_data = []
    cost_data = []

    for idx, month in enumerate(month_list):
        completed_jobs = Job.objects.filter(user=request.user).filter(date_created__month=str(idx+1))

        total_frames = 0
        total_cost = 0.0

        for job in completed_jobs:
            total_frames += job.frames_count
            total_cost += job.cost

        frames_data.append(total_frames)
        cost_data.append(round(total_cost, 2))

    temp_chart['xAxis']['categories'] = month_list
    temp_chart['series'][0]['data'] = frames_data
    temp_chart['series'][1]['data'] = cost_data

    max_y = max(frames_data + [round(cost) for cost in cost_data])
    temp_chart['yAxis']['max'] = max_y * 1.25
    temp_chart['yAxis']['tickInterval'] = max_y / 5 if max_y else 50

    return temp_chart


def get_account_chart(request):

    series = [{'name': 'Frames Rendered',
               'data': [],
               'color': '#0070E0',
               'border': 2,
               'marker': {'height': 20, 'width': 20, 'symbol': static('images/chart_dot_blue.svg')}, },

              {'name': 'USD Amount Spent',
               'data': [],
               'color': '#00B712',
               'marker': {'height': 20, 'width': 20, 'symbol': static('images/chart_dot_green.svg')}}
              ]

    acc_chart_cfg['series'] = series
    chart = get_monthly_account_stats(acc_chart_cfg, request)

    return JsonResponse(chart)


def get_job_chart(request):

    """
    [{'label': '# of Votes',
      'data': [12, 19, 3, 5, 2, 3],
      'backgroundColor': [
          'rgba(255, 99, 132, 0.2)',
          'rgba(54, 162, 235, 0.2)',
          'rgba(255, 206, 86, 0.2)',
          'rgba(75, 192, 192, 0.2)',
          'rgba(153, 102, 255, 0.2)',
          'rgba(255, 159, 64, 0.2)'],
      'borderColor': [
          'rgba(255, 99, 132, 1)',
          'rgba(54, 162, 235, 1)',
          'rgba(255, 206, 86, 1)',
          'rgba(75, 192, 192, 1)',
          'rgba(153, 102, 255, 1)',
          'rgba(255, 159, 64, 1)'],
      'borderWidth': 1}]
    """

    rendering_status = JobStatus.objects.filter(name='rendering').first()
    completed_status = JobStatus.objects.filter(name='completed').first()
    failed_status = JobStatus.objects.filter(name='failed').first()
    suspended_status = JobStatus.objects.filter(name='suspended').first()

    count_rendering = Job.objects.filter(user=request.user, status=rendering_status).count()
    count_completed = Job.objects.filter(user=request.user, status=completed_status).count()
    count_failed = Job.objects.filter(user=request.user, status=failed_status).count()
    count_suspended = Job.objects.filter(user=request.user, status=suspended_status).count()

    labels = [rendering_status.display_name,
              completed_status.display_name,
              failed_status.display_name,
              suspended_status.display_name]

    if not count_rendering + count_completed + count_failed + count_suspended:
        count_completed = 1

    datasets = [{'label': 'Job Status Overview',
                 'data': [count_rendering, count_completed, count_failed, count_suspended],
                 'backgroundColor': [
                     'rgba(75, 220, 192, 0.2)',
                     'rgba(54, 162, 235, 0.2)',
                     'rgba(255, 99, 132, 0.2)',
                     'rgba(50, 50, 50, 0.2)'],
                 'borderColor': [
                     'rgba(75, 220, 192, 0.2)',
                     'rgba(54, 162, 235, 0.2)',
                     'rgba(255, 99, 132, 0.2)',
                     'rgba(50, 50, 50, 0.2)'],
                 'borderWidth': 1}]

    job_chart_cfg = {'type': 'pie', 'data': {'datasets': [],
                                             'labels': []},
                     'options': {'cutoutPercentage': 50, }}
    job_chart_cfg['data']['datasets'] = datasets
    job_chart_cfg['data']['labels'] = labels

    return JsonResponse(job_chart_cfg)

