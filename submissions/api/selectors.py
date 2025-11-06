from django.db.models import Q, QuerySet
from django.shortcuts import get_object_or_404

from surveys.api.selectors import get_form_by_uuid
from surveys.models import Question, SurveyForm

from ..models import Answer, AnswerSet


def get_all_answersets_for_form(survey_uuid: str, form_uuid: str) -> QuerySet:
    form = get_form_by_uuid(parent_uuid=survey_uuid, form_uuid=form_uuid)
    return AnswerSet.active_objects.filter(survey_form=form)


def get_all_deleted_answersets_for_form(survey_uuid: str, form_uuid: str) -> QuerySet:
    form = get_form_by_uuid(parent_uuid=survey_uuid, form_uuid=form_uuid)
    return AnswerSet.deleted_objects.filter(survey_form=form)


def get_answerset_by_uuid(uuid: str) -> AnswerSet:
    return get_object_or_404(AnswerSet, uuid=uuid)


def get_active_answeset_by_uuid(uuid: str) -> AnswerSet:
    return get_object_or_404(AnswerSet.active_objects, uuid=uuid)


def get_soft_deleted_answerset_by_uuid(uuid: str) -> AnswerSet:
    return get_object_or_404(AnswerSet.deleted_objects, uuid=uuid)


def get_radiogroup_chart(
    question: Question, all_answer_sets: QuerySet[AnswerSet]
) -> dict:
    options = question.options.all()
    total_submissions_question = Answer.active_objects.filter(
        answer_set__in=all_answer_sets,
        question=question,
    ).count()

    option_dict = {}
    for option in options:
        option_dict[option.text_value] = 0

    for option in options:
        option_dict[option.text_value] = Answer.active_objects.filter(
            answer_set__in=all_answer_sets, question=question, text_value=option.value
        ).count()

    return {
        "question_name": question.name,
        "question_title": question.title,
        "total_submissions": total_submissions_question,
        "options": option_dict,
    }


def get_checkbox_chart(
    question: Question, all_answer_sets: QuerySet[AnswerSet]
) -> dict:
    options = question.options.all()
    total_submissions_question = Answer.active_objects.filter(
        answer_set__in=all_answer_sets,
        question=question,
    ).count()

    option_dict = {}
    for option in options:
        option_dict[option.text_value] = 0

    for option in options:
        option_dict[option.text_value] = Answer.active_objects.filter(
            answer_set__in=all_answer_sets,
            question=question,
            json_value__icontains=option.value,
        ).count()

    return {
        "question_name": question.name,
        "question_title": question.title,
        "total_submissions": total_submissions_question,
        "options": option_dict,
    }


def get_boolean_chart(question: Question, all_answer_sets: QuerySet[AnswerSet]) -> dict:
    options = question.options.all()
    total_submissions_question = Answer.active_objects.filter(
        answer_set__in=all_answer_sets,
        question=question,
    ).count()

    option_dict = {}
    for option in options:
        option_dict[option.value] = 0

    for option in options:
        option_dict[option.value] = Answer.active_objects.filter(
            answer_set__in=all_answer_sets,
            question=question,
            boolean_value=option.boolean_value,
        ).count()

    return {
        "question_name": question.name,
        "question_title": question.title,
        "total_submissions": total_submissions_question,
        "options": option_dict,
    }


def chart_image_picker(
    question: Question, all_answer_sets: QuerySet[AnswerSet]
) -> dict:
    options = question.options.all()
    total_submissions_question = Answer.active_objects.filter(
        answer_set__in=all_answer_sets,
        question=question,
    ).count()

    option_dict = {}
    for option in options:
        option_dict[option.value] = 0

    for option in options:
        option_dict[option.value] = Answer.active_objects.filter(
            answer_set__in=all_answer_sets,
            question=question,
            text_value=option.value,
        ).count()

    return {
        "question_name": question.name,
        "question_title": question.title,
        "total_submissions": total_submissions_question,
        "options": option_dict,
    }


def get_charts_data(form: SurveyForm) -> list[dict]:
    all_answer_sets = AnswerSet.active_objects.filter(survey_form=form)
    chart_data = []

    questions = form.questions.filter(
        type__in=[
            "radiogroup",
            "checkbox",
            "dropdown",
            "tagbox",
            "boolean",
            "imagepicker",
        ]
    )

    for question in questions:
        if question.type in ["radiogroup", "dropdown"]:
            question_chart_data = get_radiogroup_chart(question, all_answer_sets)

        elif question.type in ["checkbox", "tagbox"]:
            question_chart_data = get_checkbox_chart(question, all_answer_sets)

        elif question.type in ["boolean"]:
            question_chart_data = get_boolean_chart(question, all_answer_sets)

        elif question.type in ["imagepicker"]:
            question_chart_data = chart_image_picker(question, all_answer_sets)

        chart_data.append(question_chart_data)

    return chart_data
