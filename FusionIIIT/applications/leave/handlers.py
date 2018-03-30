from django.contrib import messages
from django.contrib.auth.models import User
from django.db import transaction
from django.forms.formsets import formset_factory
from django.http import JsonResponse
from django.shortcuts import redirect, render, reverse

from .forms import (AcademicReplacementForm, AdminReplacementForm,
                    BaseLeaveFormSet, EmployeeCommonForm, LeaveSegmentForm)
from .helpers import deduct_leave_balance, restore_leave_balance
from .models import (HoldsDesignation, Leave, LeaveRequest, LeaveSegment,
                     LeaveType, ReplacementSegment)

LeaveFormSet = formset_factory(LeaveSegmentForm, extra=0, max_num=3, min_num=1,
                               formset=BaseLeaveFormSet)
AcadFormSet = formset_factory(AcademicReplacementForm, extra=0, max_num=3, min_num=1)
AdminFormSet = formset_factory(AdminReplacementForm, extra=0, max_num=3, min_num=1)
common_form = EmployeeCommonForm()


def add_leave_segment(form, type_of_leaves):
    data = form.cleaned_data
    leave_type = type_of_leaves.get(id=data.get('leave_type'))
    leave_segment = LeaveSegment(
        leave_type=leave_type,
        start_date=data.get('start_date'),
        end_date=data.get('end_date'),
        start_half=data.get('start_half'),
        end_half=data.get('end_half'),
        document=data.get('document')
    )
    return leave_segment


def add_acad_rep_segment(form):
    data = form.cleaned_data
    rep_user = User.objects.get(username=data.get('acad_rep'))
    rep = ReplacementSegment(
        replacer=rep_user,
        replacement_type='academic',
        start_date=data.get('acad_start_date'),
        end_date=data.get('acad_end_date')
    )
    return rep


def add_admin_rep_segment(form):
    data = form.cleaned_data
    rep_user = User.objects.get(username=data.get('admin_rep'))
    rep = ReplacementSegment(
        replacer=rep_user,
        replacement_type='administrative',
        start_date=data.get('admin_start_date'),
        end_date=data.get('admin_end_date')
    )
    return rep


@transaction.atomic
def handle_faculty_leave_application(request):
    leave_form_set = LeaveFormSet(request.POST, request.FILES, prefix='leave_form',
                                  user=request.user)
    academic_form_set = AcadFormSet(request.POST, prefix='acad_form',
                                    form_kwargs={'user': request.user})
    admin_form_set = AdminFormSet(request.POST, prefix='admin_form',
                                  form_kwargs={'user': request.user})
    common_form = EmployeeCommonForm(request.POST)

    leave_valid = leave_form_set.is_valid()
    acad_valid = academic_form_set.is_valid()
    admin_valid = admin_form_set.is_valid()
    common_valid = common_form.is_valid()

    if leave_valid and acad_valid and admin_valid and common_valid:
        leave = Leave(
            applicant=request.user
        )
        segments = list()
        type_of_leaves = LeaveType.objects.all()
        replacements = list()

        for form in leave_form_set:
            leave_segment = add_leave_segment(form, type_of_leaves)
            segments.append(leave_segment)

        for form in academic_form_set:
            rep = add_acad_rep_segment(form)
            replacements.append(rep)

        for form in admin_form_set:
            rep = add_admin_rep_segment(form)
            replacements.append(rep)

        data = common_form.cleaned_data
        leave.purpose = data.get('purpose')
        leave.is_station = data.get('is_station')
        leave.save()
        for segment in segments:
            segment.leave = leave
        for replacement in replacements:
            replacement.leave = leave
        LeaveSegment.objects.bulk_create(segments)
        ReplacementSegment.objects.bulk_create(replacements)

        deduct_leave_balance(leave)

        messages.add_message(request, messages.SUCCESS, 'Successfully Submitted !')
        return redirect(reverse('leave:leave'))

    rep_segments = request.user.rep_requests.filter(status='pending')
    leave_requests = request.user.all_leave_requests.filter(status='pending')
    leave_balance = request.user.leave_balance.all()
    user_leave_applications = Leave.objects.filter(applicant=request.user).order_by('-timestamp')
    context = {
        'leave_form_set': leave_form_set,
        'acad_form_set': academic_form_set,
        'admin_form_set': admin_form_set,
        'common_form': common_form,
        'forms': True,
        'rep_segments': rep_segments,
        'leave_balance': leave_balance,
        'leave_requests': leave_requests,
        'user_leave_applications': user_leave_applications
    }

    return render(request, 'leaveModule/leave.html', context)


def handle_staff_leave_application(request):
    leave_form_set = LeaveFormSet(request.POST, request.FILES, prefix='leave_form',
                                  user=request.user)
    admin_form_set = AdminFormSet(request.POST, prefix='admin_form',
                                  form_kwargs={'user': request.user})
    common_form = EmployeeCommonForm(request.POST)

    leave_valid = leave_form_set.is_valid()
    admin_valid = admin_form_set.is_valid()
    common_valid = common_form.is_valid()

    if leave_valid and admin_valid and common_valid:
        leave = Leave(
            applicant=request.user
        )
        segments = list()
        type_of_leaves = LeaveType.objects.all()
        replacements = list()

        for form in leave_form_set:
            leave_segment = add_leave_segment(form, type_of_leaves)
            segments.append(leave_segment)

        for form in admin_form_set:
            rep = add_admin_rep_segment(form)
            replacements.append(rep)

        data = common_form.cleaned_data
        leave.purpose = data.get('purpose')
        leave.is_station = data.get('is_station')
        leave.save()
        for segment in segments:
            segment.leave = leave
        for replacement in replacements:
            replacement.leave = leave
        LeaveSegment.objects.bulk_create(segments)
        ReplacementSegment.objects.bulk_create(replacements)

        deduct_leave_balance(leave)

        messages.add_message(request, messages.SUCCESS, 'Successfully Submitted !')
        return redirect(reverse('leave:leave'))

    leave_requests = request.user.all_leave_requests.filter(status='pending')
    rep_segments = request.user.rep_requests.filter(status='pending')
    leave_balance = request.user.leave_balance.all()
    user_leave_applications = Leave.objects.filter(applicant=request.user).order_by('-timestamp')
    context = {
        'leave_form_set': leave_form_set,
        'acad_form_set': None,
        'admin_form_set': admin_form_set,
        'common_form': common_form,
        'forms': True,
        'rep_segments': rep_segments,
        'leave_balance': leave_balance,
        'leave_requests': leave_requests,
        'user_leave_applications': user_leave_applications
    }

    return render(request, 'leaveModule/leave.html', context)


def handle_student_leave_application(request):
    pass


def send_faculty_leave_form(request):
    rep_segments = request.user.rep_requests.filter(status='pending')
    leave_requests = request.user.all_leave_requests.filter(status='pending')
    leave_balance = request.user.leave_balance.all()
    user_leave_applications = Leave.objects.filter(applicant=request.user).order_by('-timestamp')
    context = {
        'leave_form_set': LeaveFormSet(prefix='leave_form', user=request.user),
        'acad_form_set': AcadFormSet(prefix='acad_form', form_kwargs={'user': request.user}),
        'admin_form_set': AdminFormSet(prefix='admin_form', form_kwargs={'user': request.user}),
        'common_form': common_form,
        'forms': True,
        'rep_segments': rep_segments,
        'leave_balance': leave_balance,
        'leave_requests': leave_requests,
        'user_leave_applications': user_leave_applications
    }

    return render(request, 'leaveModule/leave.html', context)


def send_staff_leave_form(request):
    rep_segments = request.user.rep_requests.filter(status='pending')
    leave_balance = request.user.leave_balance.all()
    leave_requests = request.user.all_leave_requests.filter(status='pending')
    user_leave_applications = Leave.objects.filter(applicant=request.user).order_by('-timestamp')
    context = {
        'leave_form_set': LeaveFormSet(prefix='leave_form', user=request.user),
        'acad_form_set': None,
        'admin_form_set': AdminFormSet(prefix='admin_form', form_kwargs={'user': request.user}),
        'common_form': common_form,
        'forms': True,
        'rep_segments': rep_segments,
        'leave_balance': leave_balance,
        'leave_requests': leave_requests,
        'user_leave_applications': user_leave_applications
    }

    return render(request, 'leaveModule/leave.html', context)


def send_student_leave_form(request):
    pass


@transaction.atomic
def intermediary_processing(request, leave_request):
    status = request.GET.get('status')
    remark = request.GET.get('remark')
    leave_request.remark = remark
    leave = leave_request.leave
    if status == 'forward':
        leave_request.status = 'forwarded'
        leave_request.save()

        authority = leave.applicant.leave_admins.authority.designees.first().user
        LeaveRequest.objects.create(
            leave=leave_request.leave,
            requested_from=authority,
            permission='sanc_auth',
        )
        message = 'Successfully Forwarded'
    else:
        leave_request.status = 'rejected'
        leave_request.save()
        leave.status = 'rejected'
        leave.remark = 'Intermediary Rejected'
        leave.save()
        message = 'Successfully Rejected'
        restore_leave_balance(leave)

    return JsonResponse({'status': 'success', 'message': message})


@transaction.atomic
def authority_processing(request, leave_request):
    status = request.GET.get('status')
    remark = request.GET.get('remark')
    leave_request.remark = remark
    leave = leave_request.leave

    if status == 'accept':
        leave_request.status = 'accepted'
        leave_request.save()

        leave.status = 'accepted'
        leave.save()
        message = 'Successfully Accepted'

    elif status == 'forward':
        leave_request.status = 'forwarded'
        leave_request.save()

        officer = leave.applicant.leave_admins.officer.designees.first().user
        LeaveRequest.objects.create(
            leave=leave,
            requested_from=officer,
            permission='sanc_off'
        )

        message = 'Successfully Forwarded'

    else:
        leave_request.status = 'rejected'
        leave_request.save()

        leave.status = 'rejected'
        leave.remark = 'Rejected by Leave Sanctioning Authority'
        leave.save()
        restore_leave_balance(leave)
        message = 'Successfully Rejected'

    return JsonResponse({'status': 'success', 'message': message})


@transaction.atomic
def officer_processing(request, leave_request):
    status = request.GET.get('status')
    remark = request.GET.get('remark')
    leave_request.remark = remark
    leave = leave_request.leave

    if status == 'accept':
        leave_request.status = 'accepted'
        leave.status = 'accepted'
        message = 'Successfully Accepted'

    else:
        leave_request.status = 'rejected'
        leave.status = 'rejected'
        leave.remark = 'Rejected by Leave Sanctioning Officer'
        message = 'Successfully Rejected'

    leave_request.save()
    leave.save()
    return JsonResponse({'status': 'success', 'message': message})


@transaction.atomic
def process_staff_faculty_application(request):
    is_replacement_request = request.GET.get('rep')

    status = request.GET.get('status')
    id = request.GET.get('id')

    if is_replacement_request:

        with transaction.atomic():
            # TODO: Handle the Object not found error
            rep_request = ReplacementSegment.objects.get(id=id)
            if status == 'accept':
                # return JsonResponse({'status': 'success', 'message': 'Successfully Accepted'})
                rep_request.status = 'accepted'
                rep_request.remark = request.GET.get('remark')
                rep_request.save()
                if rep_request.leave.relacements_accepted():
                    leave_intermediary = HoldsDesignation.objects.get(
                                                    designation__name='Leave Intermediary').user
                    LeaveRequest.objects.create(
                        requested_from=leave_intermediary,
                        leave=rep_request.leave,
                        permission='intermediary'
                    )
                return JsonResponse({'status': 'success', 'message': 'Successfully Accepted'})

            else:
                rep_request.status = 'rejected'
                rep_request.remark = request.GET.get('remark')
                rep_request.save()
                leave = rep_request.leave
                leave.status = 'rejected'
                leave.remark = 'Replacement Request rejected.'
                leave.save()
                leave.replace_segments.filter(status='pending') \
                                      .update(status='auto rejected')

                restore_leave_balance(leave)
                return JsonResponse({'status': 'success', 'message': 'Successfully Rejected'})

    else:
        leave_request = LeaveRequest.objects.get(id=id)
        if leave_request.permission == 'intermediary':
            return intermediary_processing(request, leave_request)

        elif leave_request.permission == 'sanc_auth':
            return authority_processing(request, leave_request)

        else:
            return officer_processing(request, leave_request)


def process_student_application(request):
    pass
