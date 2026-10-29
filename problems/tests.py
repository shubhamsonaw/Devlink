from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from opportunities.models import Project
from solutions.models import Solution

from .models import Problem


class ProblemLifecycleTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='problem-owner', password='safe-test-password-123')
        self.other_user = User.objects.create_user(username='other-developer', password='safe-test-password-123')
        self.problem = Problem.objects.create(
            user=self.owner,
            title='Improve search',
            description='Make search results more useful.',
            difficulty='medium',
        )

    def create_accepted_solution(self):
        return Solution.objects.create(
            user=self.other_user,
            problem=self.problem,
            explanation='Use a ranked index.',
            is_accepted=True,
        )

    def test_owner_can_resolve_after_acceptance_and_reopen(self):
        solution = self.create_accepted_solution()
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse('set_problem_status', args=[self.problem.id]), {'status': 'resolved'}
        )
        self.assertEqual(response.status_code, 302)
        self.problem.refresh_from_db()
        self.assertEqual(self.problem.status, 'resolved')

        response = self.client.get(reverse('problem_detail', args=[self.problem.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Accepted solution')
        self.assertContains(response, 'Reopen problem')

        response = self.client.post(
            reverse('set_problem_status', args=[self.problem.id]), {'status': 'open'}
        )
        self.assertEqual(response.status_code, 302)
        self.problem.refresh_from_db()
        self.assertEqual(self.problem.status, 'open')
        self.assertEqual(solution.problem_id, self.problem.id)

    def test_cannot_resolve_without_accepted_solution_or_as_non_owner(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse('set_problem_status', args=[self.problem.id]), {'status': 'resolved'}
        )
        self.assertEqual(response.status_code, 302)
        self.problem.refresh_from_db()
        self.assertEqual(self.problem.status, 'open')

        self.create_accepted_solution()
        self.client.force_login(self.other_user)
        response = self.client.post(
            reverse('set_problem_status', args=[self.problem.id]), {'status': 'resolved'}
        )
        self.assertEqual(response.status_code, 302)
        self.problem.refresh_from_db()
        self.assertEqual(self.problem.status, 'open')

    def test_problem_waits_for_active_collaboration_project_to_finish(self):
        solution = self.create_accepted_solution()
        project = Project.objects.create(
            title='Search collaboration',
            owner=self.owner,
            source_solution=solution,
        )
        self.client.force_login(self.owner)

        response = self.client.get(reverse('problem_detail', args=[self.problem.id]))
        self.assertContains(response, 'Complete the active collaboration project')
        response = self.client.post(
            reverse('set_problem_status', args=[self.problem.id]), {'status': 'resolved'}
        )
        self.assertEqual(response.status_code, 302)
        self.problem.refresh_from_db()
        self.assertEqual(self.problem.status, 'open')

        project.status = 'completed'
        project.save(update_fields=['status'])
        response = self.client.post(
            reverse('set_problem_status', args=[self.problem.id]), {'status': 'resolved'}
        )
        self.assertEqual(response.status_code, 302)
        self.problem.refresh_from_db()
        self.assertEqual(self.problem.status, 'resolved')

    def test_accepting_a_different_solution_reopens_a_resolved_problem(self):
        previously_accepted = self.create_accepted_solution()
        new_solution = Solution.objects.create(
            user=self.other_user,
            problem=self.problem,
            explanation='An improved fix.',
            is_accepted=False,
        )
        self.problem.status = 'resolved'
        self.problem.save(update_fields=['status'])
        self.client.force_login(self.owner)

        response = self.client.post(reverse('accept_solution', args=[new_solution.id]))
        self.assertEqual(response.status_code, 302)
        previously_accepted.refresh_from_db()
        new_solution.refresh_from_db()
        self.problem.refresh_from_db()
        self.assertFalse(previously_accepted.is_accepted)
        self.assertTrue(new_solution.is_accepted)
        self.assertEqual(self.problem.status, 'open')
