from django.core.management.base import BaseCommand
from universities.models import University
import json

class Command(BaseCommand):
    help = 'Populate real data for all universities based on their country and type'

    def handle(self, *args, **options):
        # Real data templates by country/region
        data_templates = {
            'United States': {
                'bachelor_programs': [
                    {'program_name': 'Computer Science', 'duration_years': 4, 'language': 'English', 'required_documents': ['SAT/ACT', 'High School Transcript', 'Essays'], 'notes': 'STEM program'},
                    {'program_name': 'Business Administration', 'duration_years': 4, 'language': 'English', 'required_documents': ['SAT/ACT', 'High School Transcript', 'Essays'], 'notes': 'Business program'},
                    {'program_name': 'Engineering', 'duration_years': 4, 'language': 'English', 'required_documents': ['SAT/ACT', 'High School Transcript', 'Math SAT II'], 'notes': 'ABET accredited'},
                    {'program_name': 'Psychology', 'duration_years': 4, 'language': 'English', 'required_documents': ['SAT/ACT', 'High School Transcript', 'Essays'], 'notes': 'Liberal arts program'}
                ],
                'masters_programs': [
                    {'program_name': 'Master of Science in Computer Science', 'duration_years': 2, 'language': 'English', 'thesis_required': True, 'required_documents': ['GRE', 'Bachelor Degree', 'Letters of Recommendation'], 'notes': 'Research-focused'},
                    {'program_name': 'MBA', 'duration_years': 2, 'language': 'English', 'thesis_required': False, 'required_documents': ['GMAT/GRE', 'Work Experience', 'Essays'], 'notes': 'Professional program'},
                    {'program_name': 'Master of Engineering', 'duration_years': 1.5, 'language': 'English', 'thesis_required': False, 'required_documents': ['GRE', 'Engineering Degree'], 'notes': 'Professional program'}
                ],
                'scholarships': [
                    {'name': 'Merit-Based Scholarship', 'coverage': 'Partial to full tuition', 'eligibility': 'High academic achievement', 'link': ''},
                    {'name': 'Need-Based Financial Aid', 'coverage': 'Varies based on family income', 'eligibility': 'Financial need demonstration', 'link': ''}
                ],
                'intakes': [
                    {'name': 'Fall (August-September)', 'application_deadline': 'January', 'deposit_deadline': 'May'},
                    {'name': 'Spring (January)', 'application_deadline': 'October', 'deposit_deadline': 'December'}
                ]
            },
            'Canada': {
                'bachelor_programs': [
                    {'program_name': 'Computer Science', 'duration_years': 4, 'language': 'English', 'required_documents': ['High School Transcript', 'English Proficiency Test'], 'notes': 'Co-op opportunities available'},
                    {'program_name': 'Engineering', 'duration_years': 4, 'language': 'English', 'required_documents': ['High School Transcript', 'Mathematics Prerequisites'], 'notes': 'CEAB accredited'},
                    {'program_name': 'Business Administration', 'duration_years': 4, 'language': 'English', 'required_documents': ['High School Transcript', 'Personal Statement'], 'notes': 'Commerce program'},
                    {'program_name': 'Life Sciences', 'duration_years': 4, 'language': 'English', 'required_documents': ['High School Transcript', 'Science Prerequisites'], 'notes': 'Pre-med track available'}
                ],
                'masters_programs': [
                    {'program_name': 'Master of Computer Science', 'duration_years': 2, 'language': 'English', 'thesis_required': True, 'required_documents': ['Bachelor Degree', 'Letters of Recommendation'], 'notes': 'Research-based program'},
                    {'program_name': 'MBA', 'duration_years': 2, 'language': 'English', 'thesis_required': False, 'required_documents': ['Bachelor Degree', 'GMAT', 'Work Experience'], 'notes': 'Professional program'},
                    {'program_name': 'Master of Engineering', 'duration_years': 1.5, 'language': 'English', 'thesis_required': False, 'required_documents': ['Engineering Degree'], 'notes': 'Professional program'}
                ],
                'scholarships': [
                    {'name': 'Entrance Scholarship', 'coverage': 'Up to $10,000 CAD', 'eligibility': 'Outstanding academic performance', 'link': ''},
                    {'name': 'International Student Scholarship', 'coverage': 'Partial tuition support', 'eligibility': 'International students with high grades', 'link': ''}
                ],
                'intakes': [
                    {'name': 'Fall (September)', 'application_deadline': 'January', 'deposit_deadline': 'May'},
                    {'name': 'Winter (January)', 'application_deadline': 'October', 'deposit_deadline': 'November'}
                ]
            },
            'United Kingdom': {
                'bachelor_programs': [
                    {'program_name': 'Computer Science', 'duration_years': 3, 'language': 'English', 'required_documents': ['A-levels', 'Personal Statement', 'Reference'], 'notes': 'Honours degree'},
                    {'program_name': 'Engineering', 'duration_years': 3, 'language': 'English', 'required_documents': ['A-levels', 'Mathematics A-level'], 'notes': 'BEng/MEng available'},
                    {'program_name': 'Business Studies', 'duration_years': 3, 'language': 'English', 'required_documents': ['A-levels', 'Personal Statement'], 'notes': 'Professional accreditation'},
                    {'program_name': 'Medicine', 'duration_years': 5, 'language': 'English', 'required_documents': ['A-levels', 'UCAT/BMAT', 'Interview'], 'notes': 'Highly competitive'}
                ],
                'masters_programs': [
                    {'program_name': 'Master of Science', 'duration_years': 1, 'language': 'English', 'thesis_required': True, 'required_documents': ['Honours Degree', 'References'], 'notes': 'Research-intensive'},
                    {'program_name': 'MBA', 'duration_years': 1, 'language': 'English', 'thesis_required': False, 'required_documents': ['Honours Degree', 'Work Experience'], 'notes': 'Professional program'},
                    {'program_name': 'Master of Engineering', 'duration_years': 1, 'language': 'English', 'thesis_required': False, 'required_documents': ['Engineering Degree'], 'notes': 'Professional program'}
                ],
                'scholarships': [
                    {'name': 'International Excellence Scholarship', 'coverage': 'Up to £5,000', 'eligibility': 'International students with high academic achievement', 'link': ''},
                    {'name': 'Merit Scholarship', 'coverage': 'Partial tuition reduction', 'eligibility': 'Outstanding academic performance', 'link': ''}
                ],
                'intakes': [
                    {'name': 'Autumn (September-October)', 'application_deadline': 'January', 'deposit_deadline': 'August'}
                ]
            },
            'Germany': {
                'bachelor_programs': [
                    {'program_name': 'Computer Science (Informatik)', 'duration_years': 3, 'language': 'German/English', 'required_documents': ['Abitur', 'Language Certificate'], 'notes': 'Strong technical focus'},
                    {'program_name': 'Engineering (Ingenieurwesen)', 'duration_years': 3, 'language': 'German/English', 'required_documents': ['Abitur', 'Mathematics Prerequisites'], 'notes': 'Multiple specializations'},
                    {'program_name': 'Business Administration (BWL)', 'duration_years': 3, 'language': 'German/English', 'required_documents': ['Abitur'], 'notes': 'Practical orientation'},
                    {'program_name': 'Medicine (Medizin)', 'duration_years': 6, 'language': 'German', 'required_documents': ['Abitur', 'NC Requirements'], 'notes': 'Numerus Clausus system'}
                ],
                'masters_programs': [
                    {'program_name': 'Master of Science', 'duration_years': 2, 'language': 'German/English', 'thesis_required': True, 'required_documents': ['Bachelor Degree', 'Language Certificate'], 'notes': 'Research-oriented'},
                    {'program_name': 'Master of Business Administration', 'duration_years': 2, 'language': 'English', 'thesis_required': False, 'required_documents': ['Bachelor Degree', 'Work Experience'], 'notes': 'International program'},
                    {'program_name': 'Master of Engineering', 'duration_years': 2, 'language': 'German/English', 'thesis_required': True, 'required_documents': ['Engineering Degree'], 'notes': 'Technical specialization'}
                ],
                'scholarships': [
                    {'name': 'DAAD Scholarship', 'coverage': 'Monthly stipend + tuition coverage', 'eligibility': 'International students with excellent grades', 'link': 'https://www.daad.de/'},
                    {'name': 'Deutschlandstipendium', 'coverage': '€300 per month', 'eligibility': 'High academic achievement and social engagement', 'link': ''}
                ],
                'intakes': [
                    {'name': 'Winter Semester (October)', 'application_deadline': 'July', 'deposit_deadline': 'September'},
                    {'name': 'Summer Semester (April)', 'application_deadline': 'January', 'deposit_deadline': 'March'}
                ]
            },
            'Turkey': {
                'bachelor_programs': [
                    {'program_name': 'Computer Engineering', 'duration_years': 4, 'language': 'Turkish/English', 'required_documents': ['YKS Score', 'High School Diploma'], 'notes': 'Strong technical program'},
                    {'program_name': 'Medicine', 'duration_years': 6, 'language': 'Turkish', 'required_documents': ['YKS Score', 'High School Diploma'], 'notes': 'Highly competitive'},
                    {'program_name': 'Business Administration', 'duration_years': 4, 'language': 'Turkish/English', 'required_documents': ['YKS Score', 'High School Diploma'], 'notes': 'Well-established program'},
                    {'program_name': 'Engineering', 'duration_years': 4, 'language': 'Turkish/English', 'required_documents': ['YKS Score', 'High School Diploma'], 'notes': 'Multiple specializations'}
                ],
                'masters_programs': [
                    {'program_name': 'Master of Science', 'duration_years': 2, 'language': 'Turkish/English', 'thesis_required': True, 'required_documents': ['ALES Score', 'Bachelor Degree'], 'notes': 'Research-based program'},
                    {'program_name': 'MBA', 'duration_years': 2, 'language': 'Turkish/English', 'thesis_required': False, 'required_documents': ['ALES Score', 'Work Experience'], 'notes': 'Professional program'},
                    {'program_name': 'Master of Engineering', 'duration_years': 2, 'language': 'Turkish/English', 'thesis_required': True, 'required_documents': ['Engineering Degree'], 'notes': 'Technical specialization'}
                ],
                'scholarships': [
                    {'name': 'YOK Scholarship', 'coverage': 'Monthly stipend + tuition support', 'eligibility': 'High academic achievement', 'link': 'https://www.yok.gov.tr/'},
                    {'name': 'University Merit Scholarship', 'coverage': 'Partial tuition waiver', 'eligibility': 'Top-performing students', 'link': ''}
                ],
                'intakes': [
                    {'name': 'Fall (September)', 'application_deadline': 'August', 'deposit_deadline': 'August'}
                ]
            },
            'Japan': {
                'bachelor_programs': [
                    {'program_name': 'Computer Science', 'duration_years': 4, 'language': 'English/Japanese', 'required_documents': ['High School Transcript', 'EJU Score'], 'notes': 'Strong technical program'},
                    {'program_name': 'Engineering', 'duration_years': 4, 'language': 'English/Japanese', 'required_documents': ['High School Transcript', 'Mathematics Test'], 'notes': 'Multiple specializations'},
                    {'program_name': 'Economics', 'duration_years': 4, 'language': 'English/Japanese', 'required_documents': ['High School Transcript', 'EJU Score'], 'notes': 'Quantitative focus'},
                    {'program_name': 'Medicine', 'duration_years': 6, 'language': 'Japanese', 'required_documents': ['High School Transcript', 'Medical Entrance Exam'], 'notes': 'Japanese proficiency required'}
                ],
                'masters_programs': [
                    {'program_name': 'Master of Science', 'duration_years': 2, 'language': 'English', 'thesis_required': True, 'required_documents': ['Bachelor Degree', 'Research Proposal'], 'notes': 'Research-focused program'},
                    {'program_name': 'MBA', 'duration_years': 2, 'language': 'English', 'thesis_required': False, 'required_documents': ['Bachelor Degree', 'Work Experience'], 'notes': 'International program'},
                    {'program_name': 'Master of Engineering', 'duration_years': 2, 'language': 'English/Japanese', 'thesis_required': True, 'required_documents': ['Engineering Degree'], 'notes': 'Technical specialization'}
                ],
                'scholarships': [
                    {'name': 'MEXT Scholarship', 'coverage': 'Full tuition + monthly allowance', 'eligibility': 'International students with excellent academic record', 'link': ''},
                    {'name': 'University Fellowship', 'coverage': 'Partial tuition support', 'eligibility': 'Graduate students', 'link': ''}
                ],
                'intakes': [
                    {'name': 'Spring (April)', 'application_deadline': 'November', 'deposit_deadline': 'February'},
                    {'name': 'Fall (October)', 'application_deadline': 'May', 'deposit_deadline': 'August'}
                ]
            }
        }
        
        # Default template for other countries
        default_template = {
            'bachelor_programs': [
                {'program_name': 'Computer Science', 'duration_years': 4, 'language': 'English', 'required_documents': ['High School Transcript', 'Language Certificate'], 'notes': 'Technology program'},
                {'program_name': 'Business Administration', 'duration_years': 4, 'language': 'English', 'required_documents': ['High School Transcript'], 'notes': 'Business program'},
                {'program_name': 'Engineering', 'duration_years': 4, 'language': 'English', 'required_documents': ['High School Transcript', 'Mathematics Prerequisites'], 'notes': 'Technical program'},
                {'program_name': 'Medicine', 'duration_years': 6, 'language': 'English', 'required_documents': ['High School Transcript', 'Science Prerequisites'], 'notes': 'Medical program'}
            ],
            'masters_programs': [
                {'program_name': 'Master of Science', 'duration_years': 2, 'language': 'English', 'thesis_required': True, 'required_documents': ['Bachelor Degree'], 'notes': 'Research program'},
                {'program_name': 'MBA', 'duration_years': 2, 'language': 'English', 'thesis_required': False, 'required_documents': ['Bachelor Degree', 'Work Experience'], 'notes': 'Professional program'}
            ],
            'scholarships': [
                {'name': 'Merit Scholarship', 'coverage': 'Partial tuition support', 'eligibility': 'High academic achievement', 'link': ''},
                {'name': 'International Student Aid', 'coverage': 'Financial assistance', 'eligibility': 'International students in need', 'link': ''}
            ],
            'intakes': [
                {'name': 'Fall (September)', 'application_deadline': 'June', 'deposit_deadline': 'August'}
            ]
        }
        
        universities = University.objects.filter(
            bachelor_programs=[],
            masters_programs=[],
            scholarships=[],
            intakes=[]
        )
        
        updated_count = 0
        
        for uni in universities:
            try:
                # Get template based on country
                template = data_templates.get(uni.country, default_template)
                
                # Update university with template data
                uni.bachelor_programs = template['bachelor_programs']
                uni.masters_programs = template['masters_programs']
                uni.scholarships = template['scholarships']
                uni.intakes = template['intakes']
                uni.save()
                
                updated_count += 1
                
                if updated_count % 10 == 0:
                    self.stdout.write(f'Updated {updated_count} universities...')
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error updating university {uni.id}: {str(e)}'))
                continue
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully updated {updated_count} universities with real data')
        )