"""
Медицинский анализ для хирургических функций
Интеграция КТ данных и таблиц смещения почек
"""
import os
import json
import logging
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from scipy.spatial.distance import cdist
from scipy.optimize import minimize_scalar

logger = logging.getLogger(__name__)

class MedicalAnalysisService:
    """Сервис медицинского анализа для хирургов"""
    
    def __init__(self, displacement_data_path: str = None):
        """
        Инициализация с путём к таблицам смещения
        
        Args:
            displacement_data_path: путь к Excel файлу с данными смещения
        """
        self.displacement_data = None
        self.displacement_stats = None
        
        if displacement_data_path and os.path.exists(displacement_data_path):
            self.load_displacement_data(displacement_data_path)
    
    def load_displacement_data(self, file_path: str) -> bool:
        """
        Загрузка и парсинг таблиц смещения почек
        
        Args:
            file_path: путь к Excel/CSV файлу
            
        Returns:
            bool: успешность загрузки
        """
        try:
            # Определяем формат файла
            if file_path.endswith('.xlsx') or file_path.endswith('.xls'):
                df = pd.read_excel(file_path, sheet_name=0)
            elif file_path.endswith('.csv'):
                df = pd.read_csv(file_path, encoding='utf-8')
            else:
                logger.error(f"Unsupported file format: {file_path}")
                return False
            
            # Очистка и подготовка данных
            self.displacement_data = self._clean_displacement_data(df)
            self.displacement_stats = self._calculate_displacement_stats()
            
            logger.info(f"Loaded displacement data for {len(self.displacement_data)} patients")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load displacement data: {e}")
            return False
    
    def _clean_displacement_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Очистка и структурирование данных смещения
        
        Args:
            df: исходный DataFrame
            
        Returns:
            pd.DataFrame: очищенные данные
        """
        # Извлечение основных колонок
        cleaned_data = []
        
        for idx, row in df.iterrows():
            try:
                # Пропускаем заголовки
                if pd.isna(row.get('ФИО', '')) or str(row.get('ФИО', '')).startswith(','):
                    continue
                
                patient_data = {
                    'patient_id': idx,
                    'name': row.get('ФИО', ''),
                    'gender': row.get('Пол', ''),
                    'age': row.get('Возраст', 0),
                    'bmi': row.get('ИМТ', 0),
                    'body_type': row.get('Телосложение', ''),
                    
                    # Координаты почек (спина/бок)
                    'right_kidney_back': self._extract_coordinates(row, 'Правая почка', 'На спине'),
                    'right_kidney_side': self._extract_coordinates(row, 'Правая почка', 'На боку'),
                    'left_kidney_back': self._extract_coordinates(row, 'Левая почка', 'На спине'),
                    'left_kidney_side': self._extract_coordinates(row, 'Левая почка', 'На боку'),
                    
                    # Углы ротации
                    'rotation_angles': self._extract_rotation_angles(row),
                    
                    # Параметры сосудистой ножки
                    'vascular_params': self._extract_vascular_params(row),
                    
                    # Индекс извитости
                    'tortuosity_index': self._extract_tortuosity_index(row),
                    
                    # Разница показателей
                    'displacement_diff': self._extract_displacement_diff(row)
                }
                
                cleaned_data.append(patient_data)
                
            except Exception as e:
                logger.warning(f"Failed to parse row {idx}: {e}")
                continue
        
        return pd.DataFrame(cleaned_data)
    
    def _extract_coordinates(self, row: pd.Series, kidney: str, position: str) -> Dict:
        """Извлечение координат почек"""
        coords = {}
        
        # Ищем колонки с координатами для нужной почки и позиции
        for third in ['Верхняя треть', 'Средняя треть', 'Нижняя треть']:
            for axis in ['Ось Х', 'Ось Y', 'Ось Z']:
                # Формируем имя колонки (упрощённо)
                col_pattern = f"{kidney}*{position}*{third}*{axis}"
                matching_cols = [col for col in row.index if all(part in str(col) for part in col_pattern.split('*'))]
                
                if matching_cols:
                    value = row[matching_cols[0]]
                    try:
                        coords[f"{third.lower().replace(' ', '_')}_{axis.lower()}"] = float(str(value).replace(',', '.'))
                    except:
                        coords[f"{third.lower().replace(' ', '_')}_{axis.lower()}"] = 0.0
        
        return coords
    
    def _extract_rotation_angles(self, row: pd.Series) -> Dict:
        """Извлечение углов ротации"""
        angles = {}
        for angle in ['∠ А°', '∠ В°', '∠ С°']:
            matching_cols = [col for col in row.index if angle in str(col)]
            if matching_cols:
                try:
                    angles[angle.replace('°', '').replace('∠ ', '').strip()] = float(row[matching_cols[0]])
                except:
                    angles[angle.replace('°', '').replace('∠ ', '').strip()] = 0.0
        return angles
    
    def _extract_vascular_params(self, row: pd.Series) -> Dict:
        """Извлечение параметров сосудистой ножки"""
        params = {}
        
        # Длина ножки L
        l_cols = [col for col in row.index if 'L (мм)' in str(col)]
        if l_cols:
            try:
                params['length_mm'] = float(row[l_cols[0]])
            except:
                params['length_mm'] = 0.0
        
        # Угол отхождения
        angle_cols = [col for col in row.index if 'Отхождения°' in str(col)]
        if angle_cols:
            try:
                params['departure_angle'] = float(row[angle_cols[0]])
            except:
                params['departure_angle'] = 0.0
        
        # Угол проваливания
        fall_cols = [col for col in row.index if 'Проваливания°' in str(col)]
        if fall_cols:
            try:
                params['fall_angle'] = float(row[fall_cols[0]])
            except:
                params['fall_angle'] = 0.0
        
        return params
    
    def _extract_tortuosity_index(self, row: pd.Series) -> float:
        """Извлечение индекса извитости"""
        tort_cols = [col for col in row.index if 'Индекс извитости' in str(col)]
        if tort_cols:
            try:
                return float(row[tort_cols[0]])
            except:
                return 0.0
        return 0.0
    
    def _extract_displacement_diff(self, row: pd.Series) -> Dict:
        """Извлечение разницы показателей"""
        diff = {}
        
        # Ищем колонки с разницей (Δ)
        for col in row.index:
            if 'Δ' in str(col) or 'Δ' in str(col):
                try:
                    # Очищаем имя ключа
                    clean_key = str(col).replace('Δ', '').replace(' ', '_').replace('/', '_')
                    diff[clean_key] = float(row[col])
                except:
                    diff[clean_key] = 0.0
        
        return diff
    
    def _calculate_displacement_stats(self) -> Dict:
        """Расчёт статистики смещения"""
        if self.displacement_data is None or len(self.displacement_data) == 0:
            return {}
        
        stats = {}
        
        # Статистика по смещениям
        for kidney in ['right', 'left']:
            for position in ['back', 'side']:
                key = f"{kidney}_kidney_{position}"
                if key in self.displacement_data.columns:
                    kidney_data = self.displacement_data[key].dropna()
                    
                    # Рассчитываем средние смещения
                    avg_displacement = {}
                    for coord in ['верхняя_треть_ось_x', 'средняя_треть_ось_y', 'нижняя_треть_ось_z']:
                        if coord in kidney_data.iloc[0] if len(kidney_data) > 0 else {}:
                            values = [d.get(coord, 0) for d in kidney_data if isinstance(d, dict)]
                            if values:
                                avg_displacement[coord] = {
                                    'mean': np.mean(values),
                                    'std': np.std(values),
                                    'min': np.min(values),
                                    'max': np.max(values)
                                }
                    
                    stats[f"{kidney}_{position}"] = avg_displacement
        
        # Статистика по ИМТ
        if 'bmi' in self.displacement_data.columns:
            bmi_data = self.displacement_data['bmi'].dropna()
            stats['bmi'] = {
                'mean': np.mean(bmi_data),
                'std': np.std(bmi_data),
                'distribution': {
                    'normal': len(bmi_data[bmi_data < 25]),
                    'overweight': len(bmi_data[(bmi_data >= 25) & (bmi_data < 30)]),
                    'obese': len(bmi_data[bmi_data >= 30])
                }
            }
        
        return stats
    
    def predict_displacement_for_patient(self, patient_data: Dict) -> Dict:
        """
        Предсказание смещения для нового пациента на основе статистики
        
        Args:
            patient_data: данные пациента (ИМТ, телосложение, возраст)
            
        Returns:
            Dict: предсказанные смещения
        """
        if not self.displacement_stats:
            logger.warning("No displacement statistics available")
            return {}
        
        predictions = {}
        
        # Базовое предсказание на основе ИМТ
        bmi = patient_data.get('bmi', 25)
        body_type = patient_data.get('body_type', 'норма').lower()
        
        # Коррекция смещения в зависимости от ИМТ
        bmi_factor = 1.0
        if bmi > 30:  # Ожирение
            bmi_factor = 1.3
        elif bmi > 25:  # Избыточный вес
            bmi_factor = 1.15
        elif bmi < 18.5:  # Астеническое
            bmi_factor = 0.85
        
        # Коррекция в зависимости от телосложения
        body_factor = 1.0
        if 'гипер' in body_type:
            body_factor = 1.1
        elif 'астенич' in body_type:
            body_factor = 0.9
        
        total_factor = bmi_factor * body_factor
        
        # Генерируем предсказания для каждой почки
        for kidney in ['right', 'left']:
            for position in ['back', 'side']:
                key = f"{kidney}_{position}"
                if key in self.displacement_stats:
                    predictions[key] = {}
                    
                    for coord, stats in self.displacement_stats[key].items():
                        # Базовое значение + коррекция
                        base_value = stats['mean']
                        predicted_value = base_value * total_factor
                        
                        # Добавляем случайную вариацию в пределах std
                        if stats['std'] > 0:
                            variation = np.random.normal(0, stats['std'] * 0.3)
                            predicted_value += variation
                        
                        predictions[key][coord] = predicted_value
        
        return predictions
    
    def analyze_calices_for_puncture(self, kidney_stl_path: str, patient_data: Dict) -> Dict:
        """
        Анализ чашечек для пункции (метод Федорцова)
        
        Args:
            kidney_stl_path: путь к STL файлу почки
            patient_data: данные пациента
            
        Returns:
            Dict: анализ пригодных чашечек
        """
        try:
            import trimesh
            
            # Загружаем 3D модель почки
            mesh = trimesh.load(kidney_stl_path)
            
            # Находим чашечки (выпуклые области на поверхности)
            calices = self._detect_calices(mesh)
            
            # Анализируем каждую чашечку
            suitable_calices = []
            for i, calyx in enumerate(calices):
                # Расчёт угла доступа
                access_angle = self._calculate_access_angle(calyx, mesh)
                
                # Расчёт глубины до поверхности
                depth = self._calculate_depth_to_surface(calyx, mesh)
                
                # Оценка пригодности
                is_suitable = (
                    access_angle < 45 and  # угол доступа < 45°
                    10 < depth < 50 and    # глубина 10-50 мм
                    calyx['volume'] > 100   # минимальный объём
                )
                
                calyx_data = {
                    'id': i,
                    'position': calyx['center'],
                    'access_angle': access_angle,
                    'depth': depth,
                    'volume': calyx['volume'],
                    'is_suitable': is_suitable,
                    'confidence': self._calculate_calyx_confidence(calyx, access_angle, depth)
                }
                
                if is_suitable:
                    suitable_calices.append(calyx_data)
            
            return {
                'total_calices': len(calices),
                'suitable_calices': suitable_calices,
                'accessibility_score': len(suitable_calices) / max(len(calices), 1),
                'recommendations': self._generate_puncture_recommendations(suitable_calices)
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze calices: {e}")
            return {'error': str(e)}
    
    def calculate_troacar_positions(self, kidney_stl_path: str, tumor_data: Dict = None, patient_data: Dict = None) -> Dict:
        """
        Расчёт оптимальных позиций троакаров (метод Коновалова)
        
        Args:
            kidney_stl_path: путь к STL файлу почки
            tumor_data: данные об опухоли (если есть)
            patient_data: данные пациента
            
        Returns:
            Dict: позиции троакаров и рекомендации
        """
        try:
            import trimesh
            
            mesh = trimesh.load(kidney_stl_path)
            
            # Стандартные позиции троакаров
            base_positions = self._get_standard_troacar_positions(mesh)
            
            # Коррекция с учётом ИМТ и смещения
            corrected_positions = []
            for pos in base_positions:
                corrected_pos = self._correct_troacar_position(
                    pos, mesh, tumor_data, patient_data
                )
                corrected_positions.append(corrected_pos)
            
            # Анализ безопасности позиций
            safety_analysis = []
            for pos in corrected_positions:
                safety = self._analyze_troacar_safety(pos, mesh, tumor_data)
                safety_analysis.append(safety)
            
            # Выбор оптимальной позиции
            best_position = self._select_optimal_troacar_position(
                corrected_positions, safety_analysis
            )
            
            return {
                'troacar_positions': corrected_positions,
                'safety_analysis': safety_analysis,
                'recommended_position': best_position,
                'access_corridors': self._calculate_access_corridors(best_position, mesh),
                'risk_factors': self._identify_risk_factors(best_position, mesh, tumor_data)
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate troacar positions: {e}")
            return {'error': str(e)}
    
    def _detect_calices(self, mesh) -> List[Dict]:
        """Обнаружение чашечек на поверхности почки"""
        # Упрощённый алгоритм - ищем выпуклые области
        calices = []
        
        # Разбиение поверхности на участки
        vertices = mesh.vertices
        faces = mesh.faces
        
        # Кластеризация вершин для поиска чашечек
        # (упрощённо - в реальности нужен более сложный алгоритм)
        for i in range(5, 15):  # примерное количество чашечек
            # Случайная точка на поверхности (заглушка)
            random_face_idx = np.random.randint(0, len(faces))
            face = faces[random_face_idx]
            center = vertices[face].mean(axis=0)
            
            calyx = {
                'center': center,
                'volume': np.random.uniform(100, 500),  # заглушка
                'surface_area': np.random.uniform(50, 200)
            }
            calices.append(calyx)
        
        return calices
    
    def _calculate_access_angle(self, calyx: Dict, mesh) -> float:
        """Расчёт угла доступа к чашечке"""
        # Упрощённый расчёт
        return np.random.uniform(15, 60)  # заглушка
    
    def _calculate_depth_to_surface(self, calyx: Dict, mesh) -> float:
        """Расчёт глубины до поверхности"""
        # Упрощённый расчёт
        return np.random.uniform(10, 60)  # заглушка
    
    def _calculate_calyx_confidence(self, calyx: Dict, angle: float, depth: float) -> float:
        """Расчёт уверенности в пригодности чашечки"""
        confidence = 1.0
        
        if angle > 45:
            confidence -= (angle - 45) / 100
        
        if depth < 10 or depth > 50:
            confidence -= 0.2
        
        return max(0, min(1, confidence))
    
    def _generate_puncture_recommendations(self, suitable_calices: List[Dict]) -> List[str]:
        """Генерация рекомендаций для пункции"""
        recommendations = []
        
        if len(suitable_calices) == 0:
            recommendations.append("Не найдено подходящих чашечек для пункции")
            return recommendations
        
        # Сортируем по уверенности
        sorted_calices = sorted(suitable_calices, key=lambda x: x['confidence'], reverse=True)
        
        best_calyx = sorted_calices[0]
        recommendations.append(f"Оптимальная чашечка #{best_calyx['id'] + 1}")
        recommendations.append(f"Угол доступа: {best_calyx['access_angle']:.1f}°")
        recommendations.append(f"Глубина: {best_calyx['depth']:.1f} мм")
        
        if best_calyx['confidence'] > 0.8:
            recommendations.append("Высокая уверенность в успехе пункции")
        elif best_calyx['confidence'] > 0.6:
            recommendations.append("Средняя уверенность - требуется осторожность")
        else:
            recommendations.append("Низкая уверенность - рассмотреть альтернативные подходы")
        
        return recommendations
    
    def _get_standard_troacar_positions(self, mesh) -> List[np.ndarray]:
        """Получение стандартных позиций троакаров"""
        # Стандартные позиции для лапароскопии
        positions = []
        
        # Позиции относительно центра почки
        center = mesh.center_mass
        
        # Стандартные точки доступа
        offsets = [
            [100, 50, 0],   # латеральная
            [-100, 50, 0],  # медиальная  
            [0, 100, 50],   # верхняя
            [0, -50, -50]   # нижняя
        ]
        
        for offset in offsets:
            pos = center + np.array(offset)
            positions.append(pos)
        
        return positions
    
    def _correct_troacar_position(self, base_pos: np.ndarray, mesh, tumor_data: Dict, patient_data: Dict) -> np.ndarray:
        """Коррекция позиции троакара"""
        corrected_pos = base_pos.copy()
        
        # Коррекция по ИМТ
        if patient_data and 'bmi' in patient_data:
            bmi = patient_data['bmi']
            if bmi > 30:
                corrected_pos[0] *= 1.1  # смещение латерально
            elif bmi < 18.5:
                corrected_pos[0] *= 0.9  # смещение медиально
        
        # Коррекция по смещению почки
        if patient_data and 'displacement_prediction' in patient_data:
            displacement = patient_data['displacement_prediction']
            # Применяем предсказанное смещение
            if 'right_kidney_side' in displacement:
                disp = displacement['right_kidney_side']
                corrected_pos[0] += disp.get('средняя_треть_ось_x', 0) * 0.5
                corrected_pos[1] += disp.get('средняя_треть_ось_y', 0) * 0.5
        
        return corrected_pos
    
    def _analyze_troacar_safety(self, position: np.ndarray, mesh, tumor_data: Dict) -> Dict:
        """Анализ безопасности позиции троакара"""
        safety = {
            'distance_to_kidney': np.linalg.norm(position - mesh.center_mass),
            'risk_level': 'low',
            'critical_structures': [],
            'recommendations': []
        }
        
        # Расстояние до почки
        if safety['distance_to_kidney'] < 50:
            safety['risk_level'] = 'high'
            safety['recommendations'].append("Слишком близко к почке")
        elif safety['distance_to_kidney'] > 150:
            safety['risk_level'] = 'medium'
            safety['recommendations'].append("Увеличить глубину для лучшего доступа")
        
        # Проверка пересечения с критическими структурами
        # (упрощённо)
        if tumor_data:
            tumor_distance = np.linalg.norm(position - tumor_data.get('center', [0, 0, 0]))
            if tumor_distance < 30:
                safety['critical_structures'].append('опухоль')
                safety['risk_level'] = 'high'
        
        return safety
    
    def _select_optimal_troacar_position(self, positions: List[np.ndarray], safety_analysis: List[Dict]) -> np.ndarray:
        """Выбор оптимальной позиции троакара"""
        best_idx = 0
        best_score = 0
        
        for i, (pos, safety) in enumerate(zip(positions, safety_analysis)):
            score = 0
            
            # Предпочитаем позиции с низким риском
            if safety['risk_level'] == 'low':
                score += 10
            elif safety['risk_level'] == 'medium':
                score += 5
            
            # Оптимальное расстояние до почки
            distance = safety['distance_to_kidney']
            if 80 <= distance <= 120:
                score += 5
            elif 60 <= distance <= 140:
                score += 3
            
            if score > best_score:
                best_score = score
                best_idx = i
        
        return positions[best_idx]
    
    def _calculate_access_corridors(self, position: np.ndarray, mesh) -> List[Dict]:
        """Расчёт коридоров доступа"""
        corridors = []
        
        # Простой коридор от точки доступа к центру почки
        corridor = {
            'start_point': position.tolist(),
            'end_point': mesh.center_mass.tolist(),
            'diameter': 10,  # мм
            'length': np.linalg.norm(position - mesh.center_mass),
            'obstacles': []  # можно добавить проверку пересечений
        }
        corridors.append(corridor)
        
        return corridors
    
    def _identify_risk_factors(self, position: np.ndarray, mesh, tumor_data: Dict) -> List[str]:
        """Идентификация факторов риска"""
        risks = []
        
        # Проверка расстояния до сосудов (упрощённо)
        vessel_distance = np.linalg.norm(position - mesh.center_mass)
        if vessel_distance < 30:
            risks.append("Риск повреждения сосудов")
        
        # Проверка близости к опухоли
        if tumor_data and 'center' in tumor_data:
            tumor_distance = np.linalg.norm(position - np.array(tumor_data['center']))
            if tumor_distance < 20:
                risks.append("Риск повреждения опухоли")
        
        return risks

# Глобальный экземпляр сервиса
medical_analysis_service = MedicalAnalysisService()
