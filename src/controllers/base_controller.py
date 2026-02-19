"""Base controller with shared logic for CSV and ARFF controllers."""

import logging
from typing import Dict, List
import io
import base64
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PySide6.QtCore import QObject, Slot

logger = logging.getLogger(__name__)


class BaseDataController(QObject):
    """Shared base for CSVController and ARFFController.

    Subclasses must define ``self.df`` as a ``pd.DataFrame``.
    """
    
    @staticmethod
    def _format_edge(v: float) -> str:
        """Format a bin edge value for display."""
        try:
            if np.isfinite(v) and np.isclose(v, round(v)):
                return str(int(round(v)))
        except Exception:
            pass
        try:
            s = f"{float(v):.2f}"
            s = s.rstrip('0').rstrip('.')
            return s
        except Exception:
            return str(v)
    
    def _can_convert_to_numeric(self, column: pd.Series) -> tuple[bool, str]:
        """Check if a column can be converted to numeric (supports comma as decimal separator)."""
        try:
            converted = pd.to_numeric(column.dropna(), errors='coerce')
            invalid_count = converted.isna().sum()
            
            if invalid_count == 0:
                return True, ''
            
            column_normalized = column.dropna().astype(str).str.replace(',', '.', regex=False)
            converted = pd.to_numeric(column_normalized, errors='coerce')
            invalid_count = converted.isna().sum()
            
            if invalid_count == 0:
                return True, ''
            
            return False, f'A coluna contém {invalid_count} valores não numéricos.'
        except Exception as e:
            return False, f'Erro ao validar conversão: {str(e)}'
    
    def _can_convert_to_date(self, column: pd.Series) -> tuple[bool, str]:
        """Check if a column can be converted to a date type."""
        try:
            pd.to_datetime(column.dropna(), errors='raise')
            return True, ''
        except Exception:
            return False, 'Formato de data não reconhecido. Use: YYYY-MM-DD, DD/MM/YYYY, etc.'
    
    @Slot(str, str, result='QVariantMap')
    def validateTypeConversion(self, attribute_name: str, new_type: str) -> Dict:
        """Validate whether a type conversion is possible based on the original data.

        Returns:
            Dict with 'valid' (bool) and 'message' (str).
        """
        column = self._get_column(attribute_name)
        if column is None:
            return {'valid': False, 'message': 'Coluna não encontrada'}
        
        if new_type in ('String', 'Nominal'):
            return {'valid': True, 'message': ''}
        
        validators = {
            'Numeric': self._can_convert_to_numeric,
            'Date': self._can_convert_to_date
        }
        
        validator = validators.get(new_type)
        if validator:
            is_valid, error_msg = validator(column)
            return {'valid': is_valid, 'message': error_msg}
        
        return {'valid': True, 'message': ''}
    
    def _get_column(self, attribute_name: str) -> pd.Series | None:
        """Return a DataFrame column by attribute name, or None if not found."""
        if not hasattr(self, 'df') or self.df is None:
            return None
        if attribute_name not in self.df.columns:
            return None
        return self.df[attribute_name]
    
    @Slot(str, result='QVariantMap')
    def getColumnStatistics(self, attribute_name: str) -> Dict:
        """Compute descriptive statistics for a column.

        Returns numeric stats (min, max, mean, median, std) or
        categorical stats (unique count, mode), plus total and null counts.
        """
        column = self._get_column(attribute_name)
        if column is None:
            return {}
        
        stats = {}
        
        try:
            stats['count'] = int(column.count())
            stats['nullCount'] = int(column.isna().sum())
            
            # Check user-selected type, not the current pandas dtype
            selected_type = None
            if hasattr(self, 'getSuggestedType'):
                selected_type = self.getSuggestedType(attribute_name)
            
            if selected_type == 'Numeric':
                try:
                    column_normalized = column.dropna().astype(str).str.replace(',', '.', regex=False)
                    column_numeric = pd.to_numeric(column_normalized, errors='coerce')
                    
                    stats['min'] = float(column_numeric.min()) if not column_numeric.empty else 0.0
                    stats['max'] = float(column_numeric.max()) if not column_numeric.empty else 0.0
                    stats['mean'] = float(column_numeric.mean()) if not column_numeric.empty else 0.0
                    stats['median'] = float(column_numeric.median()) if not column_numeric.empty else 0.0
                    stats['std'] = float(column_numeric.std()) if not column_numeric.empty else 0.0
                except Exception:
                    # Fallback to categorical if conversion fails
                    mode_result = column.mode()
                    stats['mode'] = str(mode_result[0]) if len(mode_result) > 0 else ""
                    stats['uniqueCount'] = int(column.nunique())
            elif pd.api.types.is_numeric_dtype(column):
                stats['min'] = float(column.min()) if not column.empty else 0.0
                stats['max'] = float(column.max()) if not column.empty else 0.0
                stats['mean'] = float(column.mean()) if not column.empty else 0.0
                stats['median'] = float(column.median()) if not column.empty else 0.0
                stats['std'] = float(column.std()) if not column.empty else 0.0
            else:
                mode_result = column.mode()
                stats['mode'] = str(mode_result[0]) if len(mode_result) > 0 else ""
                stats['uniqueCount'] = int(column.nunique())
                
        except Exception as e:
            logger.warning("Error computing statistics for %s: %s", attribute_name, e)
        
        return stats

    def _generate_chart_data_url(
        self,
        attribute_name: str,
        bins: int,
        fmt: str,
        width_px: int | None = None,
        height_px: int | None = None,
    ) -> str:
        column = self._get_column(attribute_name)
        if column is None:
            return ""

        fmt = (fmt or "png").lower().strip()
        if fmt not in {"png", "svg"}:
            fmt = "png"

        try:
            # matplotlib/numpy require positive integer bins
            try:
                bins = int(bins)
            except Exception:
                bins = 10
            if bins <= 0:
                bins = 10

            column = column.dropna()
            if column.empty:
                return ""

            # Render at target size to avoid blur from upscaling in QML
            # For SVG, dpi/figsize doesn't affect text quality like PNG
            dpi = 144
            if width_px is not None and height_px is not None:
                # Keep a comfortable minimum to accommodate labels without collapsing layout
                width_px = int(max(320, min(4000, width_px)))
                height_px = int(max(220, min(3000, height_px)))
                fig_w = width_px / dpi
                fig_h = height_px / dpi
            else:
                fig_w, fig_h = 6, 4

            # Transparent background for blending with the app; avoid constrained_layout
            # which can collapse on small figures with long decorations
            fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=dpi)
            fig.patch.set_alpha(0)
            ax.set_facecolor('none')

            selected_type = None
            if hasattr(self, 'getSuggestedType'):
                selected_type = self.getSuggestedType(attribute_name)

            is_numeric = pd.api.types.is_numeric_dtype(column)
            if selected_type == 'Numeric' and not is_numeric:
                try:
                    column_normalized = column.astype(str).str.replace(',', '.', regex=False)
                    column = pd.to_numeric(column_normalized, errors='coerce').dropna()
                    is_numeric = True
                except Exception:
                    is_numeric = False

            if is_numeric:
                values = column.values.astype(float)

                bin_edges = np.histogram_bin_edges(values, bins=bins)
                counts, _ = np.histogram(values, bins=bin_edges)
                lefts = bin_edges[:-1]
                widths = bin_edges[1:] - bin_edges[:-1]
                centers = (bin_edges[:-1] + bin_edges[1:]) / 2

                ax.bar(lefts, counts, width=widths, align='edge',
                       color='#ffc107', edgecolor='black', alpha=0.7)

                labels = [f"{self._format_edge(float(bin_edges[i]))}–{self._format_edge(float(bin_edges[i + 1]))}" for i in range(len(counts))]
                # Reduce tick count when many bins to keep labels readable
                n = len(labels)
                if n > 12:
                    step = int(np.ceil(n / 8))
                    keep = [0] + list(range(0, n, step)) + [n - 1]
                    keep = sorted(set([k for k in keep if 0 <= k < n]))
                    tick_pos = centers[keep]
                    tick_lab = [labels[i] for i in keep]
                else:
                    tick_pos = centers
                    tick_lab = labels

                ax.set_xticks(tick_pos)
                ax.set_xticklabels(tick_lab, rotation=45, ha='right', color='white')
                for t in ax.get_xticklabels():
                    t.set_fontsize(8)

                ax.tick_params(axis='x', pad=2)

                ax.set_xlabel('Intervalos', color='white')
                ax.set_ylabel('Frequência', color='white')
                ax.set_title(f'Histograma - {attribute_name}', color='white', fontsize=12)
            else:
                value_counts = column.value_counts().head(10)
                ax.bar(range(len(value_counts)), value_counts.values,
                       color='#2196f3', edgecolor='black', alpha=0.7)
                ax.set_xticks(range(len(value_counts)))
                labels = [str(x)[:15] for x in value_counts.index]
                ax.set_xticklabels(labels, rotation=45, ha='right', color='white')
                ax.tick_params(axis='x', pad=2)
                for t in ax.get_xticklabels():
                    t.set_fontsize(9)
                ax.set_xlabel('Categorias', color='white')
                ax.set_ylabel('Contagem', color='white')
                ax.set_title(f'Distribuição - {attribute_name}', color='white', fontsize=12)

            ax.tick_params(colors='white')
            for spine in ax.spines.values():
                spine.set_color('white')

            # Manual margins are more predictable than layout engines for small figures
            fig.subplots_adjust(left=0.10, right=0.98, top=0.90, bottom=0.30)

            buffer = io.BytesIO()
            plt.savefig(buffer, format=fmt, transparent=True, facecolor='none', edgecolor='none')
            buffer.seek(0)
            payload = base64.b64encode(buffer.read()).decode()
            plt.close(fig)

            mime = 'image/png' if fmt == 'png' else 'image/svg+xml'
            return f"data:{mime};base64,{payload}"
        except Exception as e:
            logger.warning("Error generating chart for %s: %s", attribute_name, e)
            return ""
    
    @Slot(str, int, result=str)
    def generateChartImage(self, attribute_name: str, bins: int = 10) -> str:
        """Generate a chart as a base64 PNG data URL."""
        return self._generate_chart_data_url(attribute_name, bins, "png")

    @Slot(str, int, int, int, result=str)
    def generateChartImageSized(self, attribute_name: str, bins: int, width_px: int, height_px: int) -> str:
        """Generate a PNG at the requested pixel size for crisp text rendering."""
        return self._generate_chart_data_url(attribute_name, bins, "png", width_px=width_px, height_px=height_px)

    @Slot(str, int, result=str)
    def generateChartSvg(self, attribute_name: str, bins: int = 10) -> str:
        """Generate a transparent-background SVG chart."""
        return self._generate_chart_data_url(attribute_name, bins, "svg")
    
    @Slot(str, int, result='QVariantList')
    def getHistogramData(self, attribute_name: str, bins: int = 10) -> List:
        """Return histogram data for continuous values as a list of {bin, count} dicts."""
        column = self._get_column(attribute_name)
        if column is None:
            return []
        
        column = column.dropna()
        
        if not pd.api.types.is_numeric_dtype(column) or column.empty:
            return []
        
        try:
            try:
                bins = int(bins)
            except Exception:
                bins = 10
            if bins <= 0:
                bins = 10

            counts, bins = pd.cut(column, bins=bins, retbins=True, duplicates='drop')
            value_counts = counts.value_counts().sort_index()
            
            result = []
            for interval, count in value_counts.items():
                bin_label = f"{interval.left:.2f}-{interval.right:.2f}"
                result.append({'bin': bin_label, 'count': int(count)})
            
            return result
        except Exception as e:
            logger.warning("Error generating histogram for %s: %s", attribute_name, e)
            return []

    @Slot(str, int, result='QVariantMap')
    def getHistogramChartData(self, attribute_name: str, bins: int = 10) -> Dict:
        """Return chart-ready data for QtCharts (BarSeries).

        Returns:
            {labels, counts, xTitle, yTitle, isNumeric}
        """
        column = self._get_column(attribute_name)
        if column is None:
            return {}

        try:
            try:
                bins = int(bins)
            except Exception:
                bins = 10
            if bins <= 0:
                bins = 10

            column = column.dropna()
            if column.empty:
                return {}

            selected_type = None
            if hasattr(self, 'getSuggestedType'):
                try:
                    selected_type = self.getSuggestedType(attribute_name)
                except Exception:
                    selected_type = None

            x = column
            is_numeric = pd.api.types.is_numeric_dtype(x)
            if selected_type == 'Numeric' and not is_numeric:
                try:
                    x_norm = x.astype(str).str.replace(',', '.', regex=False)
                    x_conv = pd.to_numeric(x_norm, errors='coerce').dropna()
                    if not x_conv.empty:
                        x = x_conv
                        is_numeric = True
                except Exception:
                    is_numeric = False

            if is_numeric:
                values = x.values.astype(float)
                bin_edges = np.histogram_bin_edges(values, bins=bins)
                counts, _ = np.histogram(values, bins=bin_edges)

                labels = [f"{self._format_edge(float(bin_edges[i]))}–{self._format_edge(float(bin_edges[i + 1]))}" for i in range(len(counts))]
                return {
                    'labels': [str(l) for l in labels],
                    'counts': [int(c) for c in counts.tolist()],
                    'xTitle': 'Intervalos',
                    'yTitle': 'Frequência',
                    'isNumeric': True,
                }

            # Categórico: top 10
            value_counts = x.astype(str).value_counts().head(10)
            labels = []
            counts = []
            for v, c in value_counts.items():
                lbl = str(v)
                if len(lbl) > 20:
                    lbl = lbl[:17] + '...'
                labels.append(lbl)
                counts.append(int(c))

            return {
                'labels': labels,
                'counts': counts,
                'xTitle': 'Categorias',
                'yTitle': 'Contagem',
                'isNumeric': False,
            }

        except Exception as e:
            logger.warning("Error generating chart data for %s: %s", attribute_name, e)
            return {}
    
    @Slot(str, result='QVariantList')
    def getBarChartData(self, attribute_name: str) -> List:
        """Return bar chart data for categorical values (top 10) as {label, count} dicts."""
        column = self._get_column(attribute_name)
        if column is None:
            return []
        
        column = column.dropna()
        
        if column.empty:
            return []
        
        try:
            value_counts = column.value_counts().head(10)
            
            result = []
            for value, count in value_counts.items():
                label = str(value)
                if len(label) > 20:
                    label = label[:17] + "..."
                result.append({'label': label, 'count': int(count)})
            
            return result
        except Exception as e:
            logger.warning("Error generating bar chart for %s: %s", attribute_name, e)
            return []
    
    @Slot(str, result='QVariantList')
    def getNominalClassCounts(self, attribute_name: str) -> List:
        """Return value counts per class for nominal attributes, sorted descending."""
        column = self._get_column(attribute_name)
        if column is None:
            return []
        
        column = column.dropna()
        
        if column.empty:
            return []
        
        try:
            value_counts = column.value_counts()
            
            result = []
            for value, count in value_counts.items():
                result.append({'class': str(value), 'count': int(count)})
            
            return result
        except Exception as e:
            logger.warning("Error computing class counts for %s: %s", attribute_name, e)
            return []

    @Slot(str, str, int, result=str)
    def generateStackedChart(self, primary_attribute: str, class_attribute: str, bins: int = 10) -> str:
        """Generate a stacked chart (histogram or bar) colored by class_attribute.

        Returns a base64 PNG data URL or empty string on error.
        """
        try:
            try:
                bins = int(bins)
            except Exception:
                bins = 10
            if bins <= 0:
                bins = 10

            if not hasattr(self, 'df') or self.df is None:
                return ""

            if primary_attribute not in self.df.columns or class_attribute not in self.df.columns:
                return ""

            primary_col = self.df[primary_attribute].dropna()
            class_col = self.df[class_attribute].dropna()

            # Join on index to keep valid pairs
            joined = pd.concat([primary_col, class_col], axis=1, join='inner').dropna()
            if joined.empty:
                return ""

            x = joined.iloc[:, 0]
            grp = joined.iloc[:, 1].astype(str)

            fig, ax = plt.subplots(figsize=(6, 4), dpi=100)
            fig.patch.set_alpha(0)
            ax.set_facecolor('none')

            is_numeric = pd.api.types.is_numeric_dtype(x)

            if not is_numeric:
                try:
                    x_normalized = x.astype(str).str.replace(',', '.', regex=False)
                    x_conv = pd.to_numeric(x_normalized, errors='coerce')
                    if not x_conv.isna().all():
                        x = x_conv.dropna()
                        grp = grp.loc[x.index]
                        is_numeric = True
                except Exception:
                    is_numeric = False

            colors = plt.get_cmap('tab20').colors

            if is_numeric:
                all_vals = x.values.astype(float)
                # Use numpy for uniform bin edges to avoid outlier issues
                bin_edges = np.histogram_bin_edges(all_vals, bins=bins)

                # Sort classes by frequency for consistent color assignment
                class_totals = grp.value_counts()
                class_values = list(class_totals.index)

                n_bins = len(bin_edges) - 1
                lefts = bin_edges[:-1]
                widths = bin_edges[1:] - bin_edges[:-1]

                counts_matrix = np.zeros((len(class_values), n_bins), dtype=int)
                for i, cls in enumerate(class_values):
                    vals = x[grp == cls].values.astype(float)
                    if vals.size == 0:
                        continue
                    inds = np.digitize(vals, bin_edges) - 1
                    inds = np.clip(inds, 0, n_bins - 1)
                    for b in range(n_bins):
                        counts_matrix[i, b] = int((inds == b).sum())

                max_classes = 12
                if counts_matrix.shape[0] > max_classes:
                    top_idx = np.argsort(counts_matrix.sum(axis=1))[::-1][:max_classes]
                    other_idx = [i for i in range(counts_matrix.shape[0]) if i not in top_idx]
                    other_counts = counts_matrix[other_idx, :].sum(axis=0)
                    counts_matrix = counts_matrix[top_idx, :]
                    counts_matrix = np.vstack([counts_matrix, other_counts])
                    class_values = [class_values[i] for i in top_idx] + ['Other']

                # Use align='edge' so bars fill the bin intervals
                bottom = np.zeros(n_bins)
                for i in range(counts_matrix.shape[0]):
                    counts = counts_matrix[i]
                    ax.bar(lefts, counts, width=widths, bottom=bottom,
                           align='edge', color=colors[i % len(colors)], edgecolor='black', alpha=0.85,
                           label=str(class_values[i]))
                    bottom = bottom + counts

                bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
                ax.set_xticks(bin_centers)
                ax.set_xticklabels([f"{c:.2f}" for c in bin_centers], rotation=45, color='white')
                ax.set_xlabel(primary_attribute, color='white')
                ax.set_ylabel('Frequência', color='white')
                ax.set_title(f'Histograma empilhado - {primary_attribute} por {class_attribute}', color='white')
                leg = ax.legend(title=class_attribute)
                if leg:
                    for text in leg.get_texts():
                        text.set_color('white')
                    try:
                        leg.get_frame().set_facecolor('none')
                        leg.get_frame().set_alpha(0.0)
                    except Exception:
                        pass
                    try:
                        leg.get_frame().set_edgecolor('white')
                    except Exception:
                        pass
                    try:
                        title = leg.get_title()
                        if title is not None:
                            title.set_color('white')
                    except Exception:
                        pass

            else:
                try:
                    pivot = pd.crosstab(index=x.astype(str), columns=grp)
                    # Limit to top 10 x-axis categories for readability
                    pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=False).head(10).index]
                    bottom = np.zeros(pivot.shape[0])
                    x_positions = np.arange(pivot.shape[0])
                    for i, col_name in enumerate(pivot.columns):
                        values = pivot[col_name].values
                        ax.bar(x_positions, values, bottom=bottom, color=colors[i % len(colors)],
                               edgecolor='black', alpha=0.8, label=str(col_name))
                        bottom = bottom + values

                    ax.set_xticks(x_positions)
                    labels = [str(l)[:15] for l in pivot.index]
                    ax.set_xticklabels(labels, rotation=45, ha='right', color='white')
                    ax.set_xlabel(primary_attribute, color='white')
                    ax.set_ylabel('Contagem', color='white')
                    ax.set_title(f'Barras empilhadas - {primary_attribute} por {class_attribute}', color='white')
                    ax.legend(facecolor='none', edgecolor='white')
                    # Ensure white text in the categorical branch too
                    try:
                        leg2 = ax.get_legend()
                        if leg2:
                            for text in leg2.get_texts():
                                text.set_color('white')
                            try:
                                title2 = leg2.get_title()
                                if title2 is not None:
                                    title2.set_color('white')
                            except Exception:
                                pass
                    except Exception:
                        pass
                except Exception as e:
                    logger.warning("Error creating pivot for stacked chart: %s", e)
                    return ""

            ax.tick_params(colors='white')
            for spine in ax.spines.values():
                spine.set_color('white')

            fig.subplots_adjust(left=0.10, right=0.98, top=0.90, bottom=0.30)

            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', transparent=True, facecolor='none', edgecolor='none')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.read()).decode()
            plt.close(fig)

            return f"data:image/png;base64,{image_base64}"
        except Exception as e:
            logger.warning("Error generating stacked chart for %s / %s: %s", primary_attribute, class_attribute, e)
            return ""

    @Slot(str, str, int, result='QVariantMap')
    def getStackedHistogramData(self, primary_attribute: str, class_attribute: str, bins: int = 10) -> Dict:
        """Return data for drawing a stacked histogram on the client side.

        Returns:
            {binLefts, binWidths, binCenters, binLabels, classNames, counts}
        """
        try:
            try:
                bins = int(bins)
            except Exception:
                bins = 10
            if bins <= 0:
                bins = 10

            if not hasattr(self, 'df') or self.df is None:
                return {}

            if primary_attribute not in self.df.columns or class_attribute not in self.df.columns:
                return {}

            primary_col = self.df[primary_attribute].dropna()
            class_col = self.df[class_attribute].dropna()
            joined = pd.concat([primary_col, class_col], axis=1, join='inner').dropna()
            if joined.empty:
                return {}

            x = joined.iloc[:, 0]
            grp = joined.iloc[:, 1].astype(str)

            is_numeric = pd.api.types.is_numeric_dtype(x)
            if not is_numeric:
                try:
                    x_norm = x.astype(str).str.replace(',', '.', regex=False)
                    x_conv = pd.to_numeric(x_norm, errors='coerce')
                    if not x_conv.isna().all():
                        x = x_conv.dropna()
                        grp = grp.loc[x.index]
                        is_numeric = True
                except Exception:
                    is_numeric = False

            if not is_numeric:
                pivot = pd.crosstab(index=x.astype(str), columns=grp)
                pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=False).head(10).index]
                counts_matrix = pivot.T.values.tolist()
                class_names = list(pivot.columns.astype(str))
                # For categorical primary, bins are indices
                bin_lefts = [float(i) for i in range(len(pivot.index))]
                bin_widths = [1.0] * len(bin_lefts)
                bin_centers = [l + 0.5 for l in bin_lefts]
                bin_labels = [str(v) for v in list(pivot.index.astype(str))]

                return {
                    'binLefts': bin_lefts,
                    'binWidths': bin_widths,
                    'binCenters': bin_centers,
                    'binLabels': bin_labels,
                    'classNames': class_names,
                    'counts': counts_matrix
                }

            all_vals = x.values.astype(float)
            bin_edges = np.histogram_bin_edges(all_vals, bins=bins)
            n_bins = len(bin_edges) - 1
            lefts = bin_edges[:-1]
            widths = bin_edges[1:] - bin_edges[:-1]
            bin_centers = ((bin_edges[:-1] + bin_edges[1:]) / 2).tolist()

            bin_labels = [f"{self._format_edge(float(bin_edges[i]))}-{self._format_edge(float(bin_edges[i + 1]))}" for i in range(n_bins)]

            class_totals = grp.value_counts()
            class_values = list(class_totals.index)

            counts_matrix = []
            for cls in class_values:
                vals = x[grp == cls].values.astype(float)
                if vals.size == 0:
                    counts = [0] * n_bins
                else:
                    inds = np.digitize(vals, bin_edges) - 1
                    inds = np.clip(inds, 0, n_bins - 1)
                    counts = [int((inds == b).sum()) for b in range(n_bins)]
                counts_matrix.append(counts)

            max_classes = 12
            if len(counts_matrix) > max_classes:
                totals = [sum(row) for row in counts_matrix]
                top_idx = sorted(range(len(totals)), key=lambda i: totals[i], reverse=True)[:max_classes]
                other_idx = [i for i in range(len(totals)) if i not in top_idx]
                top_counts = [counts_matrix[i] for i in top_idx]
                other_counts = [sum(col) for col in zip(*[counts_matrix[i] for i in other_idx])] if other_idx else [0]*n_bins
                counts_matrix = top_counts + [other_counts]
                class_values = [class_values[i] for i in top_idx] + ['Other']

            return {
                'binLefts': [float(x) for x in lefts.tolist()],
                'binWidths': [float(x) for x in widths.tolist()],
                'binCenters': [float(x) for x in bin_centers],
                'binLabels': [str(x) for x in bin_labels],
                'classNames': [str(x) for x in class_values],
                'counts': counts_matrix,
                'legendTitle': str(class_attribute)
            }
            
        except Exception as e:
            logger.warning("Error generating stacked histogram data: %s", e)
            return {}
