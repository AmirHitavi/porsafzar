from collections import defaultdict

from django.db.models import QuerySet
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


def build_radiogroup_chart(question: Question, answers: list[dict]) -> dict:
    options = list(question.options.all())
    answer_map = defaultdict(int)
    for ans in answers:
        answer_map[ans["text_value"]] += 1

    option_dict = {opt.text_value: answer_map.get(opt.value, 0) for opt in options}
    total_submissions = sum(option_dict.values())

    return {
        "question_name": question.name,
        "question_title": question.title,
        "total_submissions": total_submissions,
        "options": option_dict,
    }


def build_checkbox_chart(question: Question, answers: list[dict]) -> dict:
    options = list(question.options.all())
    option_counts = {opt.text_value: 0 for opt in options}

    for ans in answers:
        json_val = ans.get("json_value")
        for opt in options:
            if opt.value in str(json_val):
                option_counts[opt.text_value] += 1

    total_submissions = len(answers)
    return {
        "question_name": question.name,
        "question_title": question.title,
        "total_submissions": total_submissions,
        "options": option_counts,
    }


def build_boolean_chart(question: Question, answers: list[dict]) -> dict:
    options = list(question.options.all())
    answer_map = defaultdict(int)
    for ans in answers:
        answer_map[ans["boolean_value"]] += 1

    option_dict = {opt.value: answer_map.get(opt.boolean_value, 0) for opt in options}
    total_submissions = sum(option_dict.values())

    return {
        "question_name": question.name,
        "question_title": question.title,
        "total_submissions": total_submissions,
        "options": option_dict,
    }


def build_imagepicker_chart(question: Question, answers: list[dict]) -> dict:
    options = list(question.options.all())
    answer_map = defaultdict(int)
    for ans in answers:
        answer_map[ans["text_value"]] += 1

    option_dict = {opt.value: answer_map.get(opt.value, 0) for opt in options}
    total_submissions = sum(option_dict.values())

    return {
        "question_name": question.name,
        "question_title": question.title,
        "total_submissions": total_submissions,
        "options": option_dict,
    }


def get_charts_data(form: SurveyForm) -> list[dict]:
    questions = list(
        form.questions.filter(
            type__in=[
                "radiogroup",
                "checkbox",
                "dropdown",
                "tagbox",
                "boolean",
                "imagepicker",
            ]
        ).prefetch_related("options")
    )

    all_answer_sets = AnswerSet.active_objects.filter(survey_form=form)

    all_answers = Answer.active_objects.filter(
        answer_set__in=all_answer_sets, question__in=questions
    ).values("question_id", "text_value", "boolean_value", "json_value")

    answers_by_question = defaultdict(list)
    for ans in all_answers:
        answers_by_question[ans["question_id"]].append(ans)

    chart_data = []
    for question in questions:
        question_answers = answers_by_question.get(question.id, [])
        if question.type in ["radiogroup", "dropdown"]:
            chart_data.append(build_radiogroup_chart(question, question_answers))
        elif question.type in ["checkbox", "tagbox"]:
            chart_data.append(build_checkbox_chart(question, question_answers))
        elif question.type == "boolean":
            chart_data.append(build_boolean_chart(question, question_answers))
        elif question.type == "imagepicker":
            chart_data.append(build_imagepicker_chart(question, question_answers))

    return chart_data
